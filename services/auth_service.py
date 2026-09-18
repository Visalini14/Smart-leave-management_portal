from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, AuditLog

def hash_password(password):
    return generate_password_hash(password)

def verify_password(stored_hash, password):
    return check_password_hash(stored_hash, password)

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                flash('Please log in first.', 'warning')
                return redirect(url_for('auth.login'))
            
            user_role = session.get('user_role')
            if user_role not in allowed_roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Unauthorized access for your role'}), 403
                flash('Access denied: You do not have permission to view this resource.', 'danger')
                return redirect(url_for('auth.unauthorized'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_audit(action, details="", user_id=None):
    if user_id is None:
        user_id = session.get('user_id')
    ip = request.remote_addr if request else "127.0.0.1"
    log = AuditLog(user_id=user_id, action=action, details=details, ip_address=ip)
    db.session.add(log)
    db.session.commit()
