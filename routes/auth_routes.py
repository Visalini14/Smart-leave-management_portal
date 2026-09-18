from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Department, LeaveType, LeaveBalance
from services.auth_service import hash_password, verify_password, login_required, log_audit

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'manager':
            return redirect(url_for('manager.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Allow login via username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if not user or not verify_password(user.password_hash, password):
            flash('Invalid username/email or password.', 'danger')
            return render_template('auth/login.html')

        if user.status == 'pending_activation':
            flash('Your account has been created by Admin but requires first-time activation! Please activate your account using your Employee Code.', 'warning')
            return redirect(url_for('auth.activate', emp_code=user.emp_code))

        if user.status != 'active':
            flash('Your account is inactive. Please contact your system administrator.', 'warning')
            return render_template('auth/login.html')

        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = user.role
        session['user_name'] = user.full_name

        log_audit("USER_LOGIN", f"User {user.username} logged in.", user_id=user.id)
        flash(f'Welcome back, {user.full_name}!', 'success')

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)

        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'manager':
            return redirect(url_for('manager.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))

    return render_template('auth/login.html')

@auth_bp.route('/activate', methods=['GET', 'POST'])
def activate():
    prefill_code = request.args.get('emp_code', '')
    
    if request.method == 'POST':
        emp_code = request.form.get('emp_code', '').strip().upper()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        user = User.query.filter_by(emp_code=emp_code).first()
        if not user:
            flash('Invalid Employee Code. Please contact your Admin for your assigned activation code.', 'danger')
            return render_template('auth/activate.html', emp_code=emp_code)

        if user.status == 'active':
            flash('This account is already activated! Please log in with your username and password.', 'info')
            return redirect(url_for('auth.login'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/activate.html', emp_code=emp_code, user=user)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return render_template('auth/activate.html', emp_code=emp_code, user=user)

        # Check if chosen username is already taken by another active user
        existing_username = User.query.filter(User.username == username, User.id != user.id).first()
        if existing_username:
            flash('That username is already taken. Please choose another username.', 'danger')
            return render_template('auth/activate.html', emp_code=emp_code, user=user)

        # Complete First-Time Activation
        user.username = username
        user.password_hash = hash_password(password)
        user.status = 'active'
        db.session.commit()

        log_audit("USER_ACTIVATED", f"Employee {user.full_name} ({user.emp_code}) activated their account.", user_id=user.id)
        flash(f'Account activated successfully for {user.full_name}! You can now log in using your new username and password.', 'success')
        return redirect(url_for('auth.login'))

    user = None
    if prefill_code:
        user = User.query.filter_by(emp_code=prefill_code).first()

    return render_template('auth/activate.html', emp_code=prefill_code, user=user)

@auth_bp.route('/register')
def register():
    flash('Public self-registration is disabled. New accounts are onboarded by System Admin. If you received an Employee Code, activate your account below.', 'info')
    return redirect(url_for('auth.activate'))

@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_audit("USER_LOGOUT", "User logged out.", user_id=user_id)
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/unauthorized')
def unauthorized():
    return render_template('auth/unauthorized.html'), 403
