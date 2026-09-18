import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, Department, LeaveType, LeaveRequest, LeaveBalance, AuditLog
from services.auth_service import login_required, role_required, hash_password, log_audit, get_current_user

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def generate_unique_emp_code():
    """Generates a unique employee activation code (e.g. EMP-4829)"""
    while True:
        num = random.randint(1000, 9999)
        code = f"EMP-{num}"
        if not User.query.filter_by(emp_code=code).first():
            return code

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    user = get_current_user()
    total_users = User.query.count()
    total_departments = Department.query.count()
    total_requests = LeaveRequest.query.count()
    pending_requests = LeaveRequest.query.filter_by(status='pending').count()
    approved_requests = LeaveRequest.query.filter_by(status='approved').count()
    rejected_requests = LeaveRequest.query.filter_by(status='rejected').count()

    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()
    recent_requests = LeaveRequest.query.order_by(LeaveRequest.applied_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        user=user,
        total_users=total_users,
        total_departments=total_departments,
        total_requests=total_requests,
        pending_requests=pending_requests,
        approved_requests=approved_requests,
        rejected_requests=rejected_requests,
        recent_logs=recent_logs,
        recent_requests=recent_requests
    )

@admin_bp.route('/users', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def users():
    user = get_current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            role = request.form.get('role', 'employee')
            dept_id = request.form.get('department_id')
            designation = request.form.get('designation', 'Staff Member')

            if User.query.filter_by(email=email).first():
                flash('An employee with this email address already exists.', 'danger')
            else:
                emp_code = generate_unique_emp_code()
                
                new_user = User(
                    emp_code=emp_code,
                    username=emp_code,
                    email=email,
                    password_hash=hash_password(emp_code),
                    full_name=full_name,
                    role=role,
                    department_id=int(dept_id) if dept_id else None,
                    designation=designation,
                    status='pending_activation'
                )
                db.session.add(new_user)
                db.session.flush()

                # Allocate default leave quotas for new account
                for lt in LeaveType.query.all():
                    db.session.add(LeaveBalance(
                        user_id=new_user.id,
                        leave_type_id=lt.id,
                        allocated_days=float(lt.max_days_per_year),
                        used_days=0.0,
                        pending_days=0.0
                    ))
                db.session.commit()
                log_audit("ADMIN_CREATE_USER", f"Onboarded employee {full_name} ({emp_code})", user_id=user.id)
                flash(f'Employee {full_name} onboarded successfully! Assigned Activation Code: {emp_code}. Provide this code to the employee for first-time account activation.', 'success')

        elif action == 'toggle_status':
            target_user_id = request.form.get('user_id', type=int)
            target_user = db.session.get(User, target_user_id)
            if target_user and target_user.id != user.id:
                target_user.status = 'inactive' if target_user.status == 'active' else 'active'
                db.session.commit()
                log_audit("ADMIN_TOGGLE_USER_STATUS", f"Updated status of {target_user.username} to {target_user.status}", user_id=user.id)
                flash(f"User {target_user.full_name} is now {target_user.status}.", 'info')

        elif action == 'update_balance':
            target_user_id = request.form.get('user_id', type=int)
            leave_type_id = request.form.get('leave_type_id', type=int)
            new_allocated = request.form.get('allocated_days', type=float, default=0.0)

            balance = LeaveBalance.query.filter_by(user_id=target_user_id, leave_type_id=leave_type_id).first()
            if not balance:
                balance = LeaveBalance(user_id=target_user_id, leave_type_id=leave_type_id, allocated_days=new_allocated)
                db.session.add(balance)
            else:
                balance.allocated_days = new_allocated

            db.session.commit()
            log_audit("ADMIN_UPDATE_BALANCE", f"Updated leave quota for User #{target_user_id} to {new_allocated} days", user_id=user.id)
            flash('Leave balance quota updated successfully.', 'success')

        return redirect(url_for('admin.users'))

    all_users = User.query.order_by(User.created_at.desc()).all()
    departments = Department.query.all()
    leave_types = LeaveType.query.all()
    return render_template('admin/users.html', user=user, users=all_users, departments=departments, leave_types=leave_types)

@admin_bp.route('/leave-types', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def leave_types():
    user = get_current_user()
    if request.method == 'POST':
        action = request.form.get('action', 'create')

        if action == 'create':
            name = request.form.get('name', '').strip()
            code = request.form.get('code', '').strip().upper()
            max_days = request.form.get('max_days_per_year', type=int, default=12)
            desc = request.form.get('description', '').strip()

            if LeaveType.query.filter_by(code=code).first():
                flash(f'Leave type code {code} already exists.', 'danger')
            else:
                new_lt = LeaveType(name=name, code=code, max_days_per_year=max_days, description=desc)
                db.session.add(new_lt)
                db.session.flush()

                for u in User.query.all():
                    db.session.add(LeaveBalance(
                        user_id=u.id,
                        leave_type_id=new_lt.id,
                        allocated_days=float(max_days)
                    ))
                db.session.commit()
                log_audit("ADMIN_ADD_LEAVE_TYPE", f"Added leave type {code} ({name})", user_id=user.id)
                flash(f'Leave type {name} added successfully.', 'success')

        elif action == 'edit':
            lt_id = request.form.get('leave_type_id', type=int)
            lt = db.session.get(LeaveType, lt_id)
            if lt:
                name = request.form.get('name', '').strip()
                code = request.form.get('code', '').strip().upper()
                max_days = request.form.get('max_days_per_year', type=int, default=12)
                desc = request.form.get('description', '').strip()

                existing = LeaveType.query.filter(LeaveType.code == code, LeaveType.id != lt_id).first()
                if existing:
                    flash(f'Leave type code {code} is already used by another policy.', 'danger')
                else:
                    lt.name = name
                    lt.code = code
                    lt.max_days_per_year = max_days
                    lt.description = desc
                    db.session.commit()
                    log_audit("ADMIN_EDIT_LEAVE_TYPE", f"Updated leave policy {code} ({name})", user_id=user.id)
                    flash(f'Leave policy {name} updated successfully.', 'success')

        elif action == 'delete':
            lt_id = request.form.get('leave_type_id', type=int)
            lt = db.session.get(LeaveType, lt_id)
            if lt:
                LeaveBalance.query.filter_by(leave_type_id=lt_id).delete()
                db.session.delete(lt)
                db.session.commit()
                log_audit("ADMIN_DELETE_LEAVE_TYPE", f"Deleted leave type {lt.code} ({lt.name})", user_id=user.id)
                flash(f'Leave policy {lt.name} deleted successfully.', 'info')

        return redirect(url_for('admin.leave_types'))

    ltypes = LeaveType.query.all()
    return render_template('admin/leave_types.html', user=user, leave_types=ltypes)

@admin_bp.route('/departments', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def departments():
    user = get_current_user()
    if request.method == 'POST':
        action = request.form.get('action', 'create')

        if action == 'create':
            name = request.form.get('name', '').strip()
            code = request.form.get('code', '').strip().upper()
            manager_id = request.form.get('manager_id', type=int)

            if Department.query.filter_by(code=code).first():
                flash(f'Department code {code} already exists.', 'danger')
            else:
                dept = Department(name=name, code=code, manager_id=manager_id if manager_id else None)
                db.session.add(dept)
                db.session.commit()
                log_audit("ADMIN_ADD_DEPARTMENT", f"Created department {code} ({name})", user_id=user.id)
                flash(f'Department {name} created successfully.', 'success')

        elif action == 'edit':
            dept_id = request.form.get('department_id', type=int)
            dept = db.session.get(Department, dept_id)
            if dept:
                name = request.form.get('name', '').strip()
                code = request.form.get('code', '').strip().upper()
                manager_id = request.form.get('manager_id', type=int)

                existing = Department.query.filter(Department.code == code, Department.id != dept_id).first()
                if existing:
                    flash(f'Department code {code} is already used by another department.', 'danger')
                else:
                    dept.name = name
                    dept.code = code
                    dept.manager_id = manager_id if manager_id else None
                    db.session.commit()
                    log_audit("ADMIN_EDIT_DEPARTMENT", f"Updated department #{dept_id} ({code})", user_id=user.id)
                    flash(f'Department {name} updated successfully.', 'success')

        elif action == 'delete':
            dept_id = request.form.get('department_id', type=int)
            dept = db.session.get(Department, dept_id)
            if dept:
                # Unassign employees from deleted department
                users_in_dept = User.query.filter_by(department_id=dept_id).all()
                for u in users_in_dept:
                    u.department_id = None
                
                db.session.delete(dept)
                db.session.commit()
                log_audit("ADMIN_DELETE_DEPARTMENT", f"Deleted department {dept.code} ({dept.name})", user_id=user.id)
                flash(f'Department {dept.name} deleted successfully.', 'info')

        return redirect(url_for('admin.departments'))

    depts = Department.query.all()
    managers = User.query.filter(User.role.in_(['manager', 'admin'])).all()
    return render_template('admin/departments.html', user=user, departments=depts, managers=managers)

@admin_bp.route('/reports')
@login_required
@role_required('admin', 'manager')
def reports():
    user = get_current_user()
    
    leave_types = LeaveType.query.all()
    type_labels = [lt.name for lt in leave_types]
    type_counts = []
    for lt in leave_types:
        cnt = LeaveRequest.query.filter_by(leave_type_id=lt.id, status='approved').count()
        type_counts.append(cnt)

    depts = Department.query.all()
    dept_labels = [d.name for d in depts]
    dept_counts = []
    for d in depts:
        cnt = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id).filter(User.department_id == d.id, LeaveRequest.status == 'approved').count()
        dept_counts.append(cnt)

    return render_template(
        'admin/reports.html',
        user=user,
        type_labels=type_labels,
        type_counts=type_counts,
        dept_labels=dept_labels,
        dept_counts=dept_counts
    )

@admin_bp.route('/audit-logs')
@login_required
@role_required('admin')
def audit_logs():
    user = get_current_user()
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/audit_logs.html', user=user, logs=logs)
