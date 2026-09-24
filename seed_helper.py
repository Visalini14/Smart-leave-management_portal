from datetime import datetime, date, timedelta
from models import db, User, Department, LeaveType, LeaveBalance, LeaveRequest, AIAnalysis, Notification, AuditLog
from services.auth_service import hash_password
from services.leave_service import create_leave_request, process_leave_request

def auto_seed_if_empty():
    """Auto-seeds database if departments/leave types do not exist yet (e.g. on Vercel /tmp db)"""
    if User.query.filter_by(username="alex_dev").first() is not None:
        return  # DB already populated with demo users

    print("Auto-seeding empty database...")
    
    # Departments
    eng_dept = Department(name="Engineering & Technology", code="ENG")
    hr_dept = Department(name="Human Resources", code="HR")
    pd_dept = Department(name="Product & Design", code="PD")
    fin_dept = Department(name="Finance & Operations", code="FIN")
    db.session.add_all([eng_dept, hr_dept, pd_dept, fin_dept])
    db.session.flush()

    # Leave Types
    cl = LeaveType(name="Casual Leave", code="CL", max_days_per_year=12, description="Short term casual or personal leave.")
    sl = LeaveType(name="Sick Leave", code="SL", max_days_per_year=10, description="Medical and health wellness leave.")
    el = LeaveType(name="Earned Leave", code="EL", max_days_per_year=15, description="Accrued annual vacation leave.")
    ml = LeaveType(name="Parental / Maternity Leave", code="ML", max_days_per_year=90, description="Parental care and family leave.")
    db.session.add_all([cl, sl, el, ml])
    db.session.flush()

    # Users
    admin_user = User(
        emp_code="EMP-1000",
        username="admin",
        email="admin@company.com",
        password_hash=hash_password("admin123"),
        full_name="Eleanor Vance (Admin)",
        role="admin",
        designation="Chief System Administrator",
        department_id=hr_dept.id,
        status="active"
    )

    eng_manager = User(
        emp_code="EMP-1001",
        username="manager_eng",
        email="m.eng@company.com",
        password_hash=hash_password("manager123"),
        full_name="Marcus Brody",
        role="manager",
        designation="VP of Engineering",
        department_id=eng_dept.id,
        status="active"
    )

    hr_manager = User(
        emp_code="EMP-1002",
        username="manager_hr",
        email="m.hr@company.com",
        password_hash=hash_password("manager123"),
        full_name="Sophia Martinez",
        role="manager",
        designation="HR Director",
        department_id=hr_dept.id,
        status="active"
    )

    emp_alex = User(
        emp_code="EMP-1003",
        username="alex_dev",
        email="alex@company.com",
        password_hash=hash_password("emp123"),
        full_name="Alex Rivera",
        role="employee",
        designation="Senior Backend Engineer",
        department_id=eng_dept.id,
        status="active"
    )

    emp_sarah = User(
        emp_code="EMP-1004",
        username="sarah_ui",
        email="sarah@company.com",
        password_hash=hash_password("emp123"),
        full_name="Sarah Chen",
        role="employee",
        designation="Lead Frontend Architect",
        department_id=eng_dept.id,
        status="active"
    )

    emp_david = User(
        emp_code="EMP-1005",
        username="david_qa",
        email="david@company.com",
        password_hash=hash_password("emp123"),
        full_name="David Miller",
        role="employee",
        designation="SDET Quality Specialist",
        department_id=eng_dept.id,
        status="active"
    )

    emp_pending = User(
        emp_code="EMP-1006",
        username="EMP-1006",
        email="rachel@company.com",
        password_hash=hash_password("EMP-1006"),
        full_name="Rachel Green (New Onboard)",
        role="employee",
        designation="Software Engineer",
        department_id=eng_dept.id,
        status="pending_activation"
    )

    db.session.add_all([admin_user, eng_manager, hr_manager, emp_alex, emp_sarah, emp_david, emp_pending])
    db.session.flush()

    eng_dept.manager_id = eng_manager.id
    hr_dept.manager_id = hr_manager.id

    users = [admin_user, eng_manager, hr_manager, emp_alex, emp_sarah, emp_david, emp_pending]
    ltypes = [cl, sl, el, ml]

    for u in users:
        for lt in ltypes:
            db.session.add(LeaveBalance(
                user_id=u.id,
                leave_type_id=lt.id,
                allocated_days=float(lt.max_days_per_year),
                used_days=0.0,
                pending_days=0.0,
                year=datetime.utcnow().year
            ))

    db.session.commit()

    today = date.today()
    start1 = today + timedelta(days=5)
    end1 = today + timedelta(days=6)
    create_leave_request(emp_alex.id, cl.id, start1, end1, "Personal family work and errand.")
    
    req1 = LeaveRequest.query.filter_by(user_id=emp_alex.id).first()
    if req1:
        process_leave_request(req1.id, eng_manager, 'approve', "Approved. Please ensure handover.")

    start2 = today + timedelta(days=5)
    end2 = timedelta(days=12) + today
    create_leave_request(emp_sarah.id, el.id, start2, end2, "Annual family vacation and road trip.")

    start3 = today + timedelta(days=2)
    end3 = today + timedelta(days=2)
    create_leave_request(emp_david.id, sl.id, start3, end3, "Medical checkup appointment.")

    print("Auto-seeding completed.")
