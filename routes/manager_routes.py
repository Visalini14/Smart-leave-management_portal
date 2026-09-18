from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, LeaveRequest, Department, AIAnalysis
from services.auth_service import login_required, role_required, get_current_user
from services.leave_service import process_leave_request

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

@manager_bp.route('/dashboard')
@login_required
@role_required('manager', 'admin')
def dashboard():
    user = get_current_user()
    
    if user.role == 'admin':
        pending_requests = LeaveRequest.query.filter_by(status='pending').order_by(LeaveRequest.applied_at.asc()).all()
        approved_requests = LeaveRequest.query.filter_by(status='approved').order_by(LeaveRequest.updated_at.desc()).limit(5).all()
        dept_users = User.query.filter_by(status='active').all()
    else:
        dept_id = user.department_id
        pending_requests = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id).filter(
            User.department_id == dept_id,
            LeaveRequest.status == 'pending'
        ).order_by(LeaveRequest.applied_at.asc()).all()
        
        approved_requests = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id).filter(
            User.department_id == dept_id,
            LeaveRequest.status == 'approved'
        ).order_by(LeaveRequest.updated_at.desc()).limit(5).all()
        
        dept_users = User.query.filter_by(department_id=dept_id, status='active').all()

    # Risk metrics
    high_risk_count = sum(1 for r in pending_requests if r.ai_analysis and r.ai_analysis.risk_level == 'High')
    med_risk_count = sum(1 for r in pending_requests if r.ai_analysis and r.ai_analysis.risk_level == 'Medium')
    low_risk_count = sum(1 for r in pending_requests if r.ai_analysis and r.ai_analysis.risk_level == 'Low')

    return render_template(
        'manager/dashboard.html',
        user=user,
        pending_requests=pending_requests,
        approved_requests=approved_requests,
        dept_users=dept_users,
        high_risk_count=high_risk_count,
        med_risk_count=med_risk_count,
        low_risk_count=low_risk_count
    )

@manager_bp.route('/pending-requests')
@login_required
@role_required('manager', 'admin')
def pending_requests():
    user = get_current_user()
    if user.role == 'admin':
        requests = LeaveRequest.query.filter_by(status='pending').order_by(LeaveRequest.applied_at.asc()).all()
    else:
        dept_id = user.department_id
        requests = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id).filter(
            User.department_id == dept_id,
            LeaveRequest.status == 'pending'
        ).order_by(LeaveRequest.applied_at.asc()).all()

    return render_template('manager/pending_requests.html', user=user, requests=requests)

@manager_bp.route('/approve/<int:request_id>', methods=['POST'])
@login_required
@role_required('manager', 'admin')
def approve_request(request_id):
    user = get_current_user()
    comments = request.form.get('comments', '').strip()
    success, msg = process_leave_request(request_id, user, 'approve', comments)
    
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
        
    return redirect(request.referrer or url_for('manager.dashboard'))

@manager_bp.route('/reject/<int:request_id>', methods=['POST'])
@login_required
@role_required('manager', 'admin')
def reject_request(request_id):
    user = get_current_user()
    comments = request.form.get('comments', '').strip()
    if not comments:
        flash('Please provide a reason for rejecting the leave request.', 'warning')
        return redirect(request.referrer or url_for('manager.dashboard'))

    success, msg = process_leave_request(request_id, user, 'reject', comments)
    
    if success:
        flash(msg, 'info')
    else:
        flash(msg, 'danger')
        
    return redirect(request.referrer or url_for('manager.dashboard'))

@manager_bp.route('/team-calendar')
@login_required
@role_required('manager', 'admin')
def team_calendar():
    user = get_current_user()
    if user.role == 'admin':
        approved_leaves = LeaveRequest.query.filter_by(status='approved').all()
    else:
        approved_leaves = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id).filter(
            User.department_id == user.department_id,
            LeaveRequest.status == 'approved'
        ).all()
        
    return render_template('manager/team_calendar.html', user=user, leaves=approved_leaves)
