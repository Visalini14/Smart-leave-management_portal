import os
import json
from datetime import datetime
import mongoengine
from mongoengine import (
    Document, StringField, IntField, FloatField, BooleanField, 
    DateTimeField, SequenceField
)
from mongoengine.queryset import Q, QNode

# Initialize MongoEngine connection
def init_db(app=None):
    mongo_uri = os.environ.get('MONGO_URI') or os.environ.get('MONGODB_URI')
    if app and not mongo_uri:
        mongo_uri = app.config.get('MONGO_URI')
    
    if mongo_uri and mongo_uri.startswith('mongodb'):
        try:
            mongoengine.connect(host=mongo_uri, serverSelectionTimeoutMS=2000)
            print(f"[MongoDB] Connected successfully to cluster.")
            return
        except Exception as e:
            print(f"[MongoDB] Connection to {mongo_uri} failed: {e}. Falling back to mongomock...")
    
    # Fallback to mongomock for local testing when no remote/local Mongo service is active
    import mongomock
    mongoengine.connect('smart_leave_db', mongo_client_class=mongomock.MongoClient)
    print("[MongoDB] Connected to in-memory MongoMock database.")

# Monkey patch BaseField to support SQLAlchemy-style query expressions
def _f_eq(self, other):
    if other is None:
        return Q(**{self.name: None})
    if isinstance(self, StringField) and isinstance(other, str):
        return Q(**{f"{self.name}__iexact": other})
    return Q(**{self.name: other})

def _f_ne(self, other):
    return Q(**{f"{self.name}__ne": other})

def _f_lt(self, other):
    return Q(**{f"{self.name}__lt": other})

def _f_lte(self, other):
    return Q(**{f"{self.name}__lte": other})

def _f_gt(self, other):
    return Q(**{f"{self.name}__gt": other})

def _f_gte(self, other):
    return Q(**{f"{self.name}__gte": other})

def _f_in(self, values):
    return Q(**{f"{self.name}__in": values})

def _f_desc(self):
    return f"-{self.name}"

def _f_asc(self):
    return f"{self.name}"

mongoengine.fields.BaseField.__eq__ = _f_eq
mongoengine.fields.BaseField.__ne__ = _f_ne
mongoengine.fields.BaseField.__lt__ = _f_lt
mongoengine.fields.BaseField.__le__ = _f_lte
mongoengine.fields.BaseField.__gt__ = _f_gt
mongoengine.fields.BaseField.__ge__ = _f_gte
mongoengine.fields.BaseField.in_ = _f_in
mongoengine.fields.BaseField.desc = _f_desc
mongoengine.fields.BaseField.asc = _f_asc

class MetaModel(type(Document)):
    def __getattr__(cls, name):
        if name == 'query':
            return MongoQuery(cls)
        raise AttributeError(f"'{cls.__name__}' object has no attribute '{name}'")

class MongoQuery:
    def __init__(self, document_cls, queryset=None):
        self.document_cls = document_cls
        self.queryset = queryset if queryset is not None else document_cls.objects.all()

    def filter_by(self, **kwargs):
        clean_kwargs = {}
        for k, v in kwargs.items():
            clean_kwargs[k] = v
        return MongoQuery(self.document_cls, self.queryset.filter(**clean_kwargs))

    def filter(self, *args):
        qs = self.queryset
        for arg in args:
            if isinstance(arg, (Q, QNode)):
                if self.document_cls == LeaveRequest:
                    try:
                        q_dict = dict(arg.query)
                        dept_id = q_dict.pop('department_id', None) or q_dict.pop('department_id__iexact', None)
                        if dept_id is not None:
                            dept_uids = [u.id for u in User.objects(department_id=dept_id)]
                            qs = qs(user_id__in=dept_uids)
                            if q_dict:
                                qs = qs(Q(**q_dict))
                            continue
                    except Exception:
                        pass
                qs = qs(arg)
            elif isinstance(arg, mongoengine.queryset.QuerySet):
                qs = arg
            elif callable(arg):
                res = arg()
                if isinstance(res, (Q, QNode)):
                    qs = qs(res)
        return MongoQuery(self.document_cls, qs)

    def get(self, doc_id):
        if doc_id is None:
            return None
        try:
            val = int(doc_id) if str(doc_id).isdigit() else doc_id
            return self.document_cls.objects(id=val).first()
        except Exception:
            return None

    def first(self):
        return self.queryset.first()

    def all(self):
        return list(self.queryset)

    def count(self):
        return self.queryset.count()

    def order_by(self, *keys):
        qs = self.queryset
        order_args = []
        for key in keys:
            if isinstance(key, str):
                order_args.append(key)
            elif hasattr(key, 'to_order_str'):
                order_args.append(key.to_order_str())
        if order_args:
            qs = qs.order_by(*order_args)
        return MongoQuery(self.document_cls, qs)

    def limit(self, n):
        return MongoQuery(self.document_cls, self.queryset.limit(n))

    def delete(self):
        return self.queryset.delete()

    def join(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter(self.all())

    def __len__(self):
        return self.count()

class BaseDocument(Document, metaclass=MetaModel):
    meta = {'abstract': True}

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if not key.startswith('_') and getattr(self, '_initialised', False) and getattr(self, 'pk', None) is not None:
            DBSession.register_dirty(self)

class Department(BaseDocument):
    meta = {'collection': 'departments'}
    id = SequenceField(primary_key=True)
    name = StringField(required=True, unique=True)
    code = StringField(required=True, unique=True)
    manager_id = IntField(default=None)
    created_at = DateTimeField(default=datetime.utcnow)

    @property
    def employees(self):
        return list(User.objects(department_id=self.id))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'manager_id': self.manager_id,
            'employee_count': len(self.employees)
        }

class User(BaseDocument):
    meta = {'collection': 'users'}
    id = SequenceField(primary_key=True)
    emp_code = StringField(unique=True, sparse=True)
    username = StringField(required=True, unique=True)
    email = StringField(required=True, unique=True)
    password_hash = StringField(required=True)
    full_name = StringField(required=True)
    role = StringField(default='employee')
    department_id = IntField(default=None)
    designation = StringField(default='Staff Member')
    status = StringField(default='pending_activation')
    created_at = DateTimeField(default=datetime.utcnow)

    @property
    def department(self):
        if self.department_id:
            return Department.objects(id=self.department_id).first()
        return None

    @property
    def leave_balances(self):
        return list(LeaveBalance.objects(user_id=self.id))

    @property
    def leave_requests(self):
        return list(LeaveRequest.objects(user_id=self.id))

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

class LeaveType(BaseDocument):
    meta = {'collection': 'leave_types'}
    id = SequenceField(primary_key=True)
    name = StringField(required=True)
    code = StringField(required=True, unique=True)
    max_days_per_year = IntField(default=12)
    requires_approval = BooleanField(default=True)
    description = StringField()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'max_days_per_year': self.max_days_per_year,
            'requires_approval': self.requires_approval,
            'description': self.description
        }

class LeaveBalance(BaseDocument):
    meta = {'collection': 'leave_balances'}
    id = SequenceField(primary_key=True)
    user_id = IntField(required=True)
    leave_type_id = IntField(required=True)
    allocated_days = FloatField(default=0.0)
    used_days = FloatField(default=0.0)
    pending_days = FloatField(default=0.0)
    year = IntField(default=lambda: datetime.utcnow().year)

    @property
    def leave_type(self):
        return LeaveType.objects(id=self.leave_type_id).first()

    @property
    def remaining_days(self):
        return max(0.0, self.allocated_days - self.used_days - self.pending_days)

    def to_dict(self):
        lt = self.leave_type
        return {
            'id': self.id,
            'user_id': self.user_id,
            'leave_type_id': self.leave_type_id,
            'leave_type_name': lt.name if lt else 'N/A',
            'leave_type_code': lt.code if lt else 'N/A',
            'allocated_days': self.allocated_days,
            'used_days': self.used_days,
            'pending_days': self.pending_days,
            'remaining_days': self.remaining_days,
            'year': self.year
        }

class LeaveRequest(BaseDocument):
    meta = {'collection': 'leave_requests'}
    id = SequenceField(primary_key=True)
    user_id = IntField(required=True)
    leave_type_id = IntField(required=True)
    start_date = DateTimeField(required=True)
    end_date = DateTimeField(required=True)
    total_days = FloatField(required=True)
    reason = StringField(required=True)
    status = StringField(default='pending')
    applied_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    processed_by_id = IntField(default=None)
    manager_comments = StringField()

    @property
    def user(self):
        return User.objects(id=self.user_id).first()

    @property
    def leave_type(self):
        return LeaveType.objects(id=self.leave_type_id).first()

    @property
    def processed_by(self):
        if self.processed_by_id:
            return User.objects(id=self.processed_by_id).first()
        return None

    @property
    def ai_analysis(self):
        return AIAnalysis.objects(leave_request_id=self.id).first()

    def to_dict(self):
        u = self.user
        lt = self.leave_type
        ai = self.ai_analysis
        return {
            'id': self.id,
            'user_id': self.user_id,
            'applicant_name': u.full_name if u else 'Unknown',
            'department_name': u.department.name if (u and u.department) else 'N/A',
            'leave_type_id': self.leave_type_id,
            'leave_type_name': lt.name if lt else 'N/A',
            'start_date': self.start_date.strftime('%Y-%m-%d') if hasattr(self.start_date, 'strftime') else str(self.start_date),
            'end_date': self.end_date.strftime('%Y-%m-%d') if hasattr(self.end_date, 'strftime') else str(self.end_date),
            'total_days': self.total_days,
            'reason': self.reason,
            'status': self.status,
            'applied_at': self.applied_at.strftime('%Y-%m-%d %H:%M') if hasattr(self.applied_at, 'strftime') else str(self.applied_at),
            'manager_comments': self.manager_comments,
            'ai_analysis': ai.to_dict() if ai else None
        }

class AIAnalysis(BaseDocument):
    meta = {'collection': 'ai_analyses'}
    id = SequenceField(primary_key=True)
    leave_request_id = IntField(required=True, unique=True)
    risk_score = FloatField(default=0.0)
    risk_level = StringField(default='Low')
    overlap_count = IntField(default=0)
    department_capacity_impact = FloatField(default=0.0)
    ai_recommendation = StringField(default='Approve Recommended')
    analysis_summary = StringField()
    risk_factors_json = StringField()
    created_at = DateTimeField(default=datetime.utcnow)

    def to_dict(self):
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

class Notification(BaseDocument):
    meta = {'collection': 'notifications'}
    id = SequenceField(primary_key=True)
    user_id = IntField(required=True)
    message = StringField(required=True)
    link = StringField()
    is_read = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(self.created_at, 'strftime') else str(self.created_at)
        }

class AuditLog(BaseDocument):
    meta = {'collection': 'audit_logs'}
    id = SequenceField(primary_key=True)
    user_id = IntField(default=None)
    action = StringField(required=True)
    details = StringField()
    ip_address = StringField()
    timestamp = DateTimeField(default=datetime.utcnow)

    @property
    def user(self):
        if self.user_id:
            return User.objects(id=self.user_id).first()
        return None

    def to_dict(self):
        u = self.user
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': u.full_name if u else 'System',
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(self.timestamp, 'strftime') else str(self.timestamp)
        }

class DBSession:
    _dirty_instances = set()

    @classmethod
    def register_dirty(cls, inst):
        cls._dirty_instances.add(inst)

    def add(self, obj):
        if hasattr(obj, 'save'):
            obj.save()

    def add_all(self, objs):
        for obj in objs:
            self.add(obj)

    def commit(self):
        for inst in list(DBSession._dirty_instances):
            try:
                inst.save()
            except Exception:
                pass
        DBSession._dirty_instances.clear()

    def flush(self):
        self.commit()

    def delete(self, obj):
        if hasattr(obj, 'delete'):
            obj.delete()

    def get(self, doc_cls, doc_id):
        if doc_id is None:
            return None
        try:
            val = int(doc_id) if str(doc_id).isdigit() else doc_id
            return doc_cls.objects(id=val).first()
        except Exception:
            return None

class DBFunc:
    def lower(self, field):
        return field
    def upper(self, field):
        return field

class DB:
    def __init__(self):
        self.session = DBSession()
        self.func = DBFunc()

    def init_app(self, app):
        init_db(app)

    def create_all(self):
        pass

    def drop_all(self):
        try:
            from mongoengine.connection import get_db
            mongo_db = get_db()
            for coll in mongo_db.list_collection_names():
                if not coll.startswith('system.'):
                    mongo_db.drop_collection(coll)
        except Exception:
            pass
        try:
            User.objects.delete()
            Department.objects.delete()
            LeaveType.objects.delete()
            LeaveBalance.objects.delete()
            LeaveRequest.objects.delete()
            AIAnalysis.objects.delete()
            Notification.objects.delete()
            AuditLog.objects.delete()
        except Exception:
            pass

db = DB()
