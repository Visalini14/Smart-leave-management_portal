import json
from datetime import datetime, timedelta
from models import db, User, LeaveRequest, LeaveBalance, LeaveType, Department, AIAnalysis

def analyze_leave_request(user_id, leave_type_id, start_date, end_date, total_days, reason):
    """
    Intelligent heuristic & pattern evaluation engine for leave requests.
    Calculates risk score (0-100), department capacity impact, overlap counts, and AI recommendation.
    """
    user = db.session.get(User, user_id)
    leave_type = db.session.get(LeaveType, leave_type_id)
    
    if not user or not leave_type:
        return None

    dept_id = user.department_id
    risk_factors = []
    base_score = 0.0

    # 1. Overlap Analysis in Department
    overlap_count = 0
    total_dept_users = 1
    
    if dept_id:
        total_dept_users = User.query.filter_by(department_id=dept_id, status='active').count() or 1
        
        # Query leaves in department overlapping with start_date and end_date
        overlapping_leaves = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id).filter(
            User.department_id == dept_id,
            LeaveRequest.user_id != user_id,
            LeaveRequest.status.in_(['approved', 'pending']),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        ).all()
        
        overlap_count = len(overlapping_leaves)
        
    capacity_impact_pct = round((overlap_count + 1) / total_dept_users * 100, 1)

    if overlap_count > 0:
        added_score = min(45, overlap_count * 20)
        base_score += added_score
        risk_factors.append(f"{overlap_count} department team member(s) already on/requested leave during this period.")

    if capacity_impact_pct > 30.0:
        base_score += 25
        risk_factors.append(f"High department capacity impact ({capacity_impact_pct}% of team absent).")

    # 2. Duration Risk
    if total_days > 10:
        base_score += 20
        risk_factors.append(f"Extended leave duration ({total_days} consecutive days).")
    elif total_days > 5:
        base_score += 10
        risk_factors.append(f"Multi-day leave request ({total_days} days).")

    # 3. Weekend / Holiday Bridge Detection
    if start_date.weekday() == 4 or end_date.weekday() == 0:
        base_score += 10
        risk_factors.append("Leave request bridges over a weekend.")

    # 4. Leave Balance Check
    balance = LeaveBalance.query.filter_by(user_id=user_id, leave_type_id=leave_type_id).first()
    if balance:
        remaining = balance.remaining_days
        if remaining < total_days:
            base_score += 35
            risk_factors.append(f"Requested days ({total_days}) exceeds current remaining balance ({remaining}).")
        elif remaining - total_days <= 1:
            base_score += 10
            risk_factors.append("Leave request will exhaust or nearly exhaust remaining balance.")

    # 5. Short Notice Check
    today = datetime.utcnow().date()
    days_in_advance = (start_date - today).days
    if days_in_advance < 2 and leave_type.code != 'SL':
        base_score += 15
        risk_factors.append(f"Submitted on short notice ({days_in_advance} day(s) before start).")

    # Final Risk Score Calculation
    final_risk_score = min(100.0, round(base_score, 1))

    if final_risk_score >= 65.0:
        risk_level = 'High'
        recommendation = 'High Capacity Risk / Review Needed'
    elif final_risk_score >= 35.0:
        risk_level = 'Medium'
        recommendation = 'Manual Review Advised'
    else:
        risk_level = 'Low'
        recommendation = 'Approve Recommended'

    # Summary synthesis
    if risk_level == 'Low':
        summary = f"Low risk request. Team capacity is well-preserved ({capacity_impact_pct}% absent). Adequate balance available."
    elif risk_level == 'Medium':
        summary = f"Moderate risk. {len(risk_factors)} factor(s) noted including department overlap or short notice. Manager review recommended."
    else:
        summary = f"High risk flag! Potential coverage conflict ({capacity_impact_pct}% capacity impacted) or balance constraint detected."

    return {
        'risk_score': final_risk_score,
        'risk_level': risk_level,
        'overlap_count': overlap_count,
        'department_capacity_impact': capacity_impact_pct,
        'ai_recommendation': recommendation,
        'analysis_summary': summary,
        'risk_factors': risk_factors
    }

def get_ai_chatbot_response(user, user_query):
    query = user_query.lower().strip()
    
    if not user:
        return "Please log in to use the AI Leave Assistant."

    if any(k in query for k in ['balance', 'how many', 'leave left', 'remaining', 'quota', 'casual', 'sick', 'earned']):
        balances = LeaveBalance.query.filter_by(user_id=user.id).all()
        if not balances:
            return "You currently have no allocated leave balances configured. Please contact HR/Admin."
        
        details = []
        for b in balances:
            details.append(f"• **{b.leave_type.name} ({b.leave_type.code})**: {b.remaining_days} days remaining (Allocated: {b.allocated_days}, Used: {b.used_days}, Pending: {b.pending_days})")
        
        return f"Hello {user.full_name}! Here is your current leave balance summary:\n\n" + "\n".join(details) + "\n\nNeed to apply for leave? Click on **Apply Leave** in your dashboard!"

    elif any(k in query for k in ['status', 'my leave', 'pending', 'request', 'applied', 'history', 'approved', 'rejected']):
        requests = LeaveRequest.query.filter_by(user_id=user.id).order_by(LeaveRequest.applied_at.desc()).limit(3).all()
        if not requests:
            return "You haven't submitted any leave requests yet."
        
        req_lines = []
        for r in requests:
            req_lines.append(f"• **{r.leave_type.name}** ({r.start_date} to {r.end_date}): Status is **{r.status.upper()}** ({r.total_days} days).")
        
        return f"Here are your recent leave applications:\n\n" + "\n".join(req_lines)

    elif any(k in query for k in ['policy', 'rule', 'notice', 'carry over', 'maternity', 'paternity', 'types', 'help']):
        ltypes = LeaveType.query.all()
        type_str = ", ".join([f"{t.name} ({t.code})" for t in ltypes])
        return (
            "📌 **Smart Leave Management Policy Summary**:\n\n"
            f"1. **Available Leave Types**: {type_str}.\n"
            "2. **Approval Process**: Applications are evaluated by the AI Risk Analyzer and routed to your Department Manager.\n"
            "3. **Short Notice**: Leave requests submitted < 2 days in advance will flag a short notice risk (except Sick Leave).\n"
            "4. **Weekend Extensions**: Leaves spanning across Fridays and Mondays are tracked for bridge impact.\n\n"
            "You can apply directly from the **Employee Dashboard**!"
        )

    elif any(k in query for k in ['apply', 'how to', 'submit', 'request leave', 'form']):
        return (
            "To submit a new leave request:\n"
            "1. Go to your **Employee Dashboard**.\n"
            "2. Click the **'Apply Leave'** button.\n"
            "3. Select Leave Type, Start Date, End Date, and write a reason.\n"
            "4. The **AI Pre-check** will instantly evaluate your request before submission!"
        )

    else:
        return (
            f"Hello {user.full_name}! I am your **AI Smart Leave Assistant** 🤖.\n\n"
            "I can help you with:\n"
            "• Checking your remaining leave balance (e.g. *'What is my casual leave balance?'*)\n"
            "• Checking status of submitted requests (e.g. *'Show my pending leave status'*)\n"
            "• Leave policies and application guidance (e.g. *'Explain leave policies'*)\n\n"
            "How can I assist you today?"
        )
