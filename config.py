import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-leave-ai-portal-secret-key-2026'
    
    # SQLite default, easily switchable to MySQL (e.g. mysql+pymysql://user:password@localhost/db_name)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'smart_leave.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # AI Settings
    MAX_DEPT_LEAVE_THRESHOLD_PERCENT = 30.0  # Max percentage of team allowed on leave concurrently
    AI_RISK_HIGH_THRESHOLD = 70.0
    AI_RISK_MEDIUM_THRESHOLD = 35.0
