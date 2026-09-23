import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# On Vercel serverless environment, the root folder is read-only.
# We store SQLite DB in /tmp/smart_leave.db if running on Vercel or Lambda environment.
if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('PORTAL_TMP_DB'):
    db_path = '/tmp/smart_leave.db'
else:
    db_path = os.path.join(BASE_DIR, 'smart_leave.db')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-leave-ai-portal-secret-key-2026'
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + db_path
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    MAX_DEPT_LEAVE_THRESHOLD_PERCENT = 30.0
    AI_RISK_HIGH_THRESHOLD = 70.0
    AI_RISK_MEDIUM_THRESHOLD = 35.0
