from flask import Flask
from flask_bootstrap import Bootstrap
# REMOVED: DebuggedApplication (This was a massive RCE hole)
import os

def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    # FIXED: Pull the SECRET_KEY from the .env file instead of hardcoding it.
    # If the .env is missing, it uses a long random-looking fallback string.
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '7f8a9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a8b0c1d2e')
    
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), '../static/images')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

    bootstrap = Bootstrap(app)

    # CRITICAL SECURITY FIX:
    # REMOVED the DebuggedApplication block. 
    # Having 'evalex=True' at '/debug' allowed anyone to run Python code 
    # in their browser to take over your Ubuntu server.
    
    # Database Setup
    from .database import create_tables
    create_tables()

    # Add Routes
    from .routes import (
        index_bp,
        login_bp,
        register_bp,
        admin_bp,
        logout_bp,
        profile_bp,
        course_bp,
        endpoint_bp,
        forgot_pass_bp,
    )

    app.register_blueprint(index_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(logout_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(endpoint_bp)
    app.register_blueprint(forgot_pass_bp)

    return app