document.addEventListener('DOMContentLoaded', () => {
    initLeavePreCheck();
    initModals();
});

// Modal helper functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('show');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('show');
}

// Live AI Leave Pre-Check & Day Calculation
function initLeavePreCheck() {
    const startDateInput = document.getElementById('apply_start_date');
    const endDateInput = document.getElementById('apply_end_date');
    const leaveTypeSelect = document.getElementById('apply_leave_type');
    const daysDisplay = document.getElementById('calculated_days_badge');
    const aiFeedbackCard = document.getElementById('ai_precheck_feedback');

    if (!startDateInput || !endDateInput) return;

    async function triggerPreCheck() {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const leaveTypeId = leaveTypeSelect ? leaveTypeSelect.value : null;

        if (!startDate || !endDate || !leaveTypeId) {
            if (aiFeedbackCard) aiFeedbackCard.style.display = 'none';
            return;
        }

        if (new Date(endDate) < new Date(startDate)) {
            if (daysDisplay) daysDisplay.textContent = 'End date cannot be prior to start date';
            if (aiFeedbackCard) aiFeedbackCard.style.display = 'none';
            return;
        }

        try {
            const res = await fetch('/api/ai/pre-check-leave', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    leave_type_id: leaveTypeId,
                    start_date: startDate,
                    end_date: endDate
                })
            });

            const data = await res.json();
            if (data.success && data.ai_analysis) {
                const ai = data.ai_analysis;

                if (daysDisplay) {
                    daysDisplay.textContent = `Total Days: ${data.calculated_days} working day(s)`;
                }

                if (aiFeedbackCard) {
                    aiFeedbackCard.style.display = 'block';
                    
                    let badgeClass = 'badge-low';
                    if (ai.risk_level === 'Medium') badgeClass = 'badge-medium';
                    if (ai.risk_level === 'High') badgeClass = 'badge-high';

                    aiFeedbackCard.innerHTML = `
                        <div style="padding: 12px; border-radius: 8px; background: #f8fafc; border: 1px solid #cbd5e1; margin-top: 12px;">
                            <div style="display:flex; justify-between; align-items:center;">
                                <strong style="font-size:0.9rem; color:#0f172a;">🤖 AI Risk Assessment:</strong>
                                <span class="badge ${badgeClass}">${ai.risk_level} Risk (${ai.risk_score}/100)</span>
                            </div>
                            <p style="font-size:0.85rem; color:#475569; margin-top:6px;">${ai.analysis_summary}</p>
                            <div style="font-size:0.8rem; color:#64748b; margin-top:4px;">
                                <span>Overlap: <strong>${ai.overlap_count} coworker(s)</strong></span> | 
                                <span>Capacity Impact: <strong>${ai.department_capacity_impact}%</strong></span>
                            </div>
                        </div>
                    `;
                }
            }
        } catch (err) {
            console.error("AI pre-check failed:", err);
        }
    }

    startDateInput.addEventListener('change', triggerPreCheck);
    endDateInput.addEventListener('change', triggerPreCheck);
    if (leaveTypeSelect) leaveTypeSelect.addEventListener('change', triggerPreCheck);
}

function initModals() {
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                backdrop.classList.remove('show');
            }
        });
    });
}

// Fetch detailed AI risk modal for managers
async function showRiskDetails(requestId) {
    const modal = document.getElementById('riskDetailsModal');
    const content = document.getElementById('riskModalContent');

    if (!modal || !content) return;

    content.innerHTML = '<p>Loading AI Analysis details...</p>';
    openModal('riskDetailsModal');

    try {
        const res = await fetch(`/api/ai/risk-details/${requestId}`);
        const data = await res.json();

        if (data.error) {
            content.innerHTML = `<p class="text-danger">${data.error}</p>`;
            return;
        }

        const ai = data.analysis;
        let riskBadge = `<span class="badge badge-${ai.risk_level.toLowerCase()}">${ai.risk_level} Risk</span>`;
        
        let factorsList = (ai.risk_factors || []).map(f => `<li>${f}</li>`).join('');
        if (!factorsList) factorsList = '<li>No significant risk flags detected.</li>';

        content.innerHTML = `
            <div style="margin-bottom: 16px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <h4 style="margin:0; font-size:1.1rem;">Applicant: ${data.applicant}</h4>
                    ${riskBadge}
                </div>
                <p style="color:#64748b; font-size:0.9rem;"><strong>Leave:</strong> ${data.leave_type} (${data.dates} - ${data.total_days} days)</p>
            </div>
            
            <div style="background:#f1f5f9; padding:12px; border-radius:8px; margin-bottom:16px;">
                <h5 style="margin-bottom:4px; font-size:0.9rem; color:#1e293b;">AI Recommendation:</h5>
                <p style="font-weight:600; color:#4f46e5; margin:0;">${ai.ai_recommendation}</p>
                <p style="font-size:0.85rem; color:#475569; margin-top:4px;">${ai.analysis_summary}</p>
            </div>

            <div style="margin-bottom:12px;">
                <h5 style="font-size:0.9rem; margin-bottom:6px;">Evaluated Risk Factors:</h5>
                <ul style="padding-left:20px; font-size:0.88rem; color:#334155;">
                    ${factorsList}
                </ul>
            </div>

            <div style="display:flex; gap:16px; font-size:0.85rem; background:#fff; padding:10px; border:1px solid #e2e8f0; border-radius:8px;">
                <div>Department Overlap: <strong>${ai.overlap_count} person(s)</strong></div>
                <div>Capacity Impact: <strong>${ai.department_capacity_impact}%</strong></div>
            </div>
        `;
    } catch (err) {
        content.innerHTML = '<p style="color:red;">Failed to fetch AI details.</p>';
    }
}
