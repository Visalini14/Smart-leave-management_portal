from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
from models import db, User, LeaveRequest, LeaveBalance, LeaveType, Notification
from services.auth_service import login_required, role_required, get_current_user
from services.leave_service import create_leave_request, cancel_leave_request

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.route('/dashboard')
@login_required
@role_required('employee', 'manager', 'admin')
def dashboard():
    user = get_current_user()
    balances = LeaveBalance.query.filter_by(user_id=user.id).all()
    leave_types = LeaveType.query.all()
    recent_requests = LeaveRequest.query.filter_by(user_id=user.id).order_by(LeaveRequest.applied_at.desc()).limit(5).all()
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(5).all()

    # Calculate summary counts
    pending_count = LeaveRequest.query.filter_by(user_id=user.id, status='pending').count()
    approved_count = LeaveRequest.query.filter_by(user_id=user.id, status='approved').count()
    rejected_count = LeaveRequest.query.filter_by(user_id=user.id, status='rejected').count()

    return render_template(
        'employee/dashboard.html',
        user=user,
        balances=balances,
        leave_types=leave_types,
        recent_requests=recent_requests,
        notifications=notifications,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count
    )

@employee_bp.route('/apply-leave', methods=['POST'])
@login_required
def apply_leave():
    user = get_current_user()
    leave_type_id = request.form.get('leave_type_id', type=int)
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    reason = request.form.get('reason', '').strip()

    if not leave_type_id or not start_date_str or not end_date_str or not reason:
        flash('All fields are required.', 'danger')
        return redirect(url_for('employee.dashboard'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('employee.dashboard'))

    success, msg, req = create_leave_request(user.id, leave_type_id, start_date, end_date, reason)
    
    if success:
        flash(f'Leave request submitted successfully! AI Risk Assessment completed.', 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('employee.dashboard'))

@employee_bp.route('/my-leaves')
@login_required
def my_leaves():
    user = get_current_user()
    status_filter = request.args.get('status', 'all')
    
    query = LeaveRequest.query.filter_by(user_id=user.id)
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
        
    requests = query.order_by(LeaveRequest.applied_at.desc()).all()
    balances = LeaveBalance.query.filter_by(user_id=user.id).all()

    return render_template('employee/my_leaves.html', user=user, requests=requests, balances=balances, current_filter=status_filter)

@employee_bp.route('/cancel-leave/<int:request_id>', methods=['POST'])
@login_required
def cancel_leave(request_id):
    user = get_current_user()
    success, msg = cancel_leave_request(request_id, user.id)
    
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
        
    return redirect(url_for('employee.my_leaves'))
