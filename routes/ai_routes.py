from flask import Blueprint, request, jsonify, session
from datetime import datetime
from models import db, User, LeaveRequest, AIAnalysis
from services.auth_service import login_required, get_current_user
from services.ai_service import get_ai_chatbot_response, analyze_leave_request

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    user = get_current_user()
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'response': 'Please type a question or prompt.'}), 400

    reply = get_ai_chatbot_response(user, message)
    return jsonify({'response': reply})

@ai_bp.route('/pre-check-leave', methods=['POST'])
@login_required
def pre_check_leave():
    user = get_current_user()
    data = request.get_json() or {}
    
    leave_type_id = data.get('leave_type_id')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    reason = data.get('reason', '')

    if not leave_type_id or not start_date_str or not end_date_str:
        return jsonify({'error': 'Missing required leave dates or leave type.'}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format.'}), 400

    if end_date < start_date:
        return jsonify({'error': 'End date must be after or equal to start date.'}), 400

    days = (end_date - start_date).days + 1
    result = analyze_leave_request(user.id, int(leave_type_id), start_date, end_date, float(days), reason)
    
    return jsonify({
        'success': True,
        'calculated_days': days,
        'ai_analysis': result
    })

@ai_bp.route('/risk-details/<int:request_id>')
@login_required
def risk_details(request_id):
    req = LeaveRequest.query.get(request_id)
    if not req:
        return jsonify({'error': 'Request not found'}), 404

    analysis = AIAnalysis.query.filter_by(leave_request_id=request_id).first()
    if not analysis:
        return jsonify({'error': 'AI Analysis record not found for this request'}), 404

    return jsonify({
        'request_id': req.id,
        'applicant': req.user.full_name,
        'leave_type': req.leave_type.name,
        'dates': f"{req.start_date} to {req.end_date}",
        'total_days': req.total_days,
        'analysis': analysis.to_dict()
    })
