from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Department(db.Model):
    __tablename__ = 'department'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id', use_alter=True, name='fk_department_manager'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    employees = db.relationship('User', backref='department', foreign_keys='User.department_id', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'manager_id': self.manager_id,
            'employee_count': len(self.employees)
        }

class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    emp_code = db.Column(db.String(20), unique=True, nullable=True)  # Unique activation code (e.g. EMP-1001)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, manager, employee
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', use_alter=True, name='fk_user_department'), nullable=True)
    designation = db.Column(db.String(100), default='Staff Member')
    status = db.Column(db.String(20), default='pending_activation')  # active, pending_activation, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    leave_balances = db.relationship('LeaveBalance', backref='user', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'emp_code': self.emp_code,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else 'N/A',
            'designation': self.designation,
            'status': self.status
        }

class LeaveType(db.Model):
    __tablename__ = 'leave_type'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    max_days_per_year = db.Column(db.Integer, default=12)
    requires_approval = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'max_days_per_year': self.max_days_per_year,
            'requires_approval': self.requires_approval,
            'description': self.description
        }

class LeaveBalance(db.Model):
    __tablename__ = 'leave_balance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_type.id'), nullable=False)
    allocated_days = db.Column(db.Float, default=0.0)
    used_days = db.Column(db.Float, default=0.0)
    pending_days = db.Column(db.Float, default=0.0)
    year = db.Column(db.Integer, default=datetime.utcnow().year)

    leave_type = db.relationship('LeaveType')

    @property
    def remaining_days(self):
        return max(0.0, self.allocated_days - self.used_days - self.pending_days)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'leave_type_id': self.leave_type_id,
            'leave_type_name': self.leave_type.name if self.leave_type else 'N/A',
            'leave_type_code': self.leave_type.code if self.leave_type else 'N/A',
            'allocated_days': self.allocated_days,
            'used_days': self.used_days,
            'pending_days': self.pending_days,
            'remaining_days': self.remaining_days,
            'year': self.year
        }

class LeaveRequest(db.Model):
    __tablename__ = 'leave_request'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_type.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Float, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, cancelled
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    manager_comments = db.Column(db.Text, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('leave_requests', cascade="all, delete-orphan"))
    leave_type = db.relationship('LeaveType')
    processed_by = db.relationship('User', foreign_keys=[processed_by_id])
    ai_analysis = db.relationship('AIAnalysis', backref='leave_request', uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'applicant_name': self.user.full_name if self.user else 'Unknown',
            'department_name': self.user.department.name if (self.user and self.user.department) else 'N/A',
            'leave_type_id': self.leave_type_id,
            'leave_type_name': self.leave_type.name if self.leave_type else 'N/A',
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'total_days': self.total_days,
            'reason': self.reason,
            'status': self.status,
            'applied_at': self.applied_at.strftime('%Y-%m-%d %H:%M'),
            'manager_comments': self.manager_comments,
            'ai_analysis': self.ai_analysis.to_dict() if self.ai_analysis else None
        }

class AIAnalysis(db.Model):
    __tablename__ = 'ai_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_request.id'), unique=True, nullable=False)
    risk_score = db.Column(db.Float, default=0.0)
    risk_level = db.Column(db.String(20), default='Low')
    overlap_count = db.Column(db.Integer, default=0)
    department_capacity_impact = db.Column(db.Float, default=0.0)
    ai_recommendation = db.Column(db.String(50), default='Approve Recommended')
    analysis_summary = db.Column(db.Text, nullable=True)
    risk_factors_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'leave_request_id': self.leave_request_id,
            'risk_score': self.risk_score,
            'risk_level': self.risk_level,
            'overlap_count': self.overlap_count,
            'department_capacity_impact': self.department_capacity_impact,
            'ai_recommendation': self.ai_recommendation,
            'analysis_summary': self.analysis_summary,
            'risk_factors': json.loads(self.risk_factors_json) if self.risk_factors_json else []
        }

class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else 'System',
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
