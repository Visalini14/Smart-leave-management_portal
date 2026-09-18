# AI-Based Smart Leave Management and Employee Portal

An enterprise-grade, intelligent full-stack Web Application designed for streamlined leave processing, automated team bandwidth risk evaluation, role-based workflow approval, and real-time interactive AI assistance.

---

## 🌟 Key Features & Modules

1. **AI Risk & Conflict Analyzer**:
   - Evaluates department overlap, team capacity impact, short notice submissions, and holiday/weekend bridging.
   - Generates risk ratings (`Low`, `Medium`, `High`) with a calculated risk score (0-100) and actionable manager recommendations.

2. **Interactive AI Assistant (Chatbot)**:
   - Embedded floating AI widget answering employee queries on leave balances, policy rules, and request statuses in natural language.

3. **Role-Based Access Control (RBAC)**:
   - **Employee Hub**: Apply for leave with live AI pre-checks, track balance quotas, view real-time request statuses.
   - **Manager Approval Center**: Inspect pending requests with AI risk breakdowns, approve/reject requests with comments, view team leave calendar.
   - **Admin Console**: Manage users, role assignments, department structures, leave type quotas, visual Chart.js analytics reports, and security audit logs.

4. **Database & ORM**:
   - Powered by **SQLAlchemy ORM**, supporting zero-config **SQLite** out of the box with 100% **MySQL** compatibility.

---

## 🚀 Quick Start Guide

### 1. Installation
Ensure Python 3.10+ is installed. Install required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Populate Database Seed Data
Run the automated seed script to generate sample departments, leave types, demo users across all roles, and initial leave requests with AI evaluations:
```bash
python seed.py
```

### 3. Launch Application Server
Start the Flask web server:
```bash
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🔑 Demo Credentials

| Role | Username | Password | Access Rights |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Full System Control, Users, Depts, Reports & Audits |
| **Manager** | `manager_eng` | `manager123` | Dept Approval Center, AI Breakdown, Team Calendar |
| **Employee 1** | `alex_dev` | `emp123` | Employee Dashboard, Apply Leave, AI Chatbot |
| **Employee 2** | `sarah_ui` | `emp123` | Employee Dashboard (Has pending multi-day request) |

---

## 📁 Project File Structure

```
c:/Prime_vecto_project/
├── app.py                      # Main Flask Application Entrypoint
├── config.py                   # App Configuration & DB URIs
├── models.py                   # SQLAlchemy Database Models
├── seed.py                     # Data Seeder Script
├── requirements.txt            # Python Dependencies
├── services/
│   ├── ai_service.py           # AI Risk Analyzer & AI Chatbot Engine
│   ├── auth_service.py         # Password Hashing, RBAC & Audit Logger
│   └── leave_service.py        # Leave Workflows & Balance Calculations
├── routes/
│   ├── admin_routes.py         # Admin Dashboard & User Management
│   ├── ai_routes.py            # AI Chat & Pre-check APIs
│   ├── auth_routes.py          # Login, Register & Session Handling
│   ├── employee_routes.py      # Employee Hub & Leave Submissions
│   └── manager_routes.py       # Manager Approvals & Risk Inspector
├── static/
│   ├── css/style.css           # Responsive Glassmorphic CSS Theme
│   └── js/
│       ├── main.js             # Live AI Pre-check & Modal Controls
│       └── ai_chat.js          # Interactive AI Assistant Drawer
└── templates/                  # Modular HTML5 Templates (Jinja2)
    ├── base.html
    ├── auth/
    ├── employee/
    ├── manager/
    └── admin/
```
