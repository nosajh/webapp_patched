from flask import Blueprint, render_template, url_for, request, redirect
import uuid, logging
from datetime import datetime, timedelta, timezone
import config 
from app.database import get_db_connection

login_bp = Blueprint("login", __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
@login_bp.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT user_id, role FROM users WHERE username = %s AND password = %s",
                        (username, password)
                    )
                    user_info = cur.fetchone()

                    if user_info is None:
                        return render_template('login.html', error="Incorrect login")

                    user_id, role = user_info
                    session_id = uuid.uuid4().hex
                    expiration_time = datetime.now(timezone.utc) + timedelta(hours=6)
                    
                    cur.execute(
                        "INSERT INTO sessions (session_id, user_id, expiration) VALUES (%s, %s, %s)",
                        (session_id, user_id, expiration_time)
                    )
                    conn.commit()

            response = redirect(url_for('admin.admin_dashboard' if role == 'admin' else 'profile.profile'))

            # --- THE NGINX SSL CHECK ---
            # Nginx will tell Flask if the outer connection was HTTPS 
            # by setting the 'X-Forwarded-Proto' header to 'https'.
            is_secure_outer = request.headers.get('X-Forwarded-Proto', 'http') == 'https'

            response.set_cookie(
                "session_id", 
                session_id, 
                expires=expiration_time, 
                httponly=True,
                samesite='Lax',
                secure=is_secure_outer # This will be True ONLY if Nginx is using SSL
            )
            return response
            
        except Exception as e:
            logging.error(f"Login error: {e}")
            return render_template('login.html', error="Error occurred")
       
    return render_template('login.html')