from flask import Flask, render_template, session
from config import Config
from models import db, User, Notification
from routes.auth_routes import auth_bp
from routes.employee_routes import employee_bp
from routes.manager_routes import manager_bp
from routes.admin_routes import admin_bp
from routes.ai_routes import ai_bp
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)

    @app.context_processor
    def inject_global_context():
        current_user = None
        unread_notif_count = 0
        if 'user_id' in session:
            current_user = db.session.get(User, session['user_id'])
            if current_user:
                unread_notif_count = Notification.query.filter_by(
                    user_id=current_user.id,
                    is_read=False
                ).count()

        return {
            'current_user': current_user,
            'unread_notif_count': unread_notif_count,
            'current_year': datetime.utcnow().year
        }

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('auth/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('auth/500.html'), 500

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    print("Starting AI-Based Smart Leave Management and Employee Portal on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
