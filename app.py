import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configure the secret key for sessions
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(24)
    
    # Configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Configure static files
    app.config["STATIC_FOLDER"] = "static"
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from routes import main_bp
    from auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    @login_manager.user_loader
    def load_user(id):
        from models import User
        return User.query.get(int(id))
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}, 200

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app