import json
from datetime import datetime, timedelta
from models import db, User, LeaveRequest, LeaveBalance, LeaveType, AIAnalysis, Notification, Department
from services.ai_service import analyze_leave_request
from services.auth_service import log_audit

def calculate_leave_days(start_date, end_date):
    """
    Calculates number of working days between start_date and end_date (excluding weekends).
    """
    current_date = start_date
    working_days = 0
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday = 0, Sunday = 6
            working_days += 1
        current_date += timedelta(days=1)
    return float(working_days) if working_days > 0 else 1.0

def create_leave_request(user_id, leave_type_id, start_date, end_date, reason):
    user = db.session.get(User, user_id)
    leave_type = db.session.get(LeaveType, leave_type_id)
    
    if not user or not leave_type:
        return False, "Invalid user or leave type.", None

    if end_date < start_date:
        return False, "End date cannot be prior to start date.", None

    total_days = calculate_leave_days(start_date, end_date)

    # Check for existing overlapping request for the same user
    overlapping = LeaveRequest.query.filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.status.in_(['pending', 'approved']),
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date
    ).first()

    if overlapping:
        return False, f"You already have a leave request ({overlapping.status}) for overlapping dates.", None

    # Check Balance
    balance = LeaveBalance.query.filter_by(user_id=user_id, leave_type_id=leave_type_id).first()
    if not balance:
        balance = LeaveBalance(
            user_id=user_id,
            leave_type_id=leave_type_id,
            allocated_days=float(leave_type.max_days_per_year),
            used_days=0.0,
            pending_days=0.0,
            year=datetime.utcnow().year
        )
        db.session.add(balance)

    if balance.remaining_days < total_days:
        return False, f"Insufficient leave balance. You have {balance.remaining_days} days remaining for {leave_type.name}, but requested {total_days} days.", None

    # Create Leave Request
    new_request = LeaveRequest(
        user_id=user_id,
        leave_type_id=leave_type_id,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        reason=reason,
        status='pending'
    )
    
    # Update pending balance
    balance.pending_days += total_days
    db.session.add(new_request)
    db.session.flush()

    # Run AI Analysis
    ai_result = analyze_leave_request(user_id, leave_type_id, start_date, end_date, total_days, reason)
    if ai_result:
        ai_record = AIAnalysis(
            leave_request_id=new_request.id,
            risk_score=ai_result['risk_score'],
            risk_level=ai_result['risk_level'],
            overlap_count=ai_result['overlap_count'],
            department_capacity_impact=ai_result['department_capacity_impact'],
            ai_recommendation=ai_result['ai_recommendation'],
            analysis_summary=ai_result['analysis_summary'],
            risk_factors_json=json.dumps(ai_result['risk_factors'])
        )
        db.session.add(ai_record)

    # Notify Manager
    manager = None
    if user.department and user.department.manager_id:
        manager = db.session.get(User, user.department.manager_id)

    if manager:
        notif = Notification(
            user_id=manager.id,
            message=f"New leave request submitted by {user.full_name} ({total_days} days, AI Risk: {ai_result['risk_level'] if ai_result else 'Low'}).",
            link="/manager/pending-requests"
        )
        db.session.add(notif)

    # Notify Admin
    admins = User.query.filter_by(role='admin').all()
    for admin in admins:
        if admin.id != (manager.id if manager else None):
            db.session.add(Notification(
                user_id=admin.id,
                message=f"Leave request submitted by {user.full_name} ({total_days} days).",
                link="/admin/dashboard"
            ))

    db.session.commit()
    log_audit("LEAVE_APPLY", f"User {user.username} requested {total_days} days of {leave_type.code}", user_id=user_id)
    
    return True, "Leave request submitted successfully!", new_request

def process_leave_request(request_id, processed_by_user, action, comments=""):
    req = db.session.get(LeaveRequest, request_id)
    if not req:
        return False, "Leave request not found."

    if req.status != 'pending':
        return False, f"Request has already been {req.status}."

    balance = LeaveBalance.query.filter_by(user_id=req.user_id, leave_type_id=req.leave_type_id).first()

    if action == 'approve':
        req.status = 'approved'
        if balance:
            balance.pending_days = max(0.0, balance.pending_days - req.total_days)
            balance.used_days += req.total_days
        
        message = f"Your leave request for {req.start_date} to {req.end_date} has been APPROVED."
    elif action == 'reject':
        req.status = 'rejected'
        if balance:
            balance.pending_days = max(0.0, balance.pending_days - req.total_days)
        
        message = f"Your leave request for {req.start_date} to {req.end_date} was REJECTED. Reason: {comments or 'No reason specified.'}"
    else:
        return False, "Invalid action specified."

    req.processed_by_id = processed_by_user.id
    req.manager_comments = comments

    # Send Notification to applicant
    notif = Notification(
        user_id=req.user_id,
        message=message,
        link="/employee/my-leaves"
    )
    db.session.add(notif)

    db.session.commit()
    log_audit(f"LEAVE_{action.upper()}", f"Request #{req.id} for {req.user.username} {action}d by {processed_by_user.username}", user_id=processed_by_user.id)

    return True, f"Leave request successfully {action}d."

def cancel_leave_request(request_id, user_id):
    req = LeaveRequest.query.filter_by(id=request_id, user_id=user_id).first()
    if not req:
        return False, "Leave request not found or access denied."

    if req.status != 'pending':
        return False, "Only pending leave requests can be cancelled."

    balance = LeaveBalance.query.filter_by(user_id=req.user_id, leave_type_id=req.leave_type_id).first()
    if balance:
        balance.pending_days = max(0.0, balance.pending_days - req.total_days)

    req.status = 'cancelled'
    db.session.commit()
    log_audit("LEAVE_CANCEL", f"User cancelled leave request #{req.id}", user_id=user_id)

    return True, "Leave request cancelled successfully."
