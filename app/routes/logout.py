from flask import Blueprint, redirect, url_for, request
import logging
import config
from app.database import get_db_connection

logout_bp = Blueprint("logout", __name__)

@logout_bp.route('/logout', methods=['GET', 'POST'])
@logout_bp.route('/logout.html', methods=['GET', 'POST'])
def logout():
    session_id = request.cookies.get("session_id")

    if session_id:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
                    conn.commit()
        except Exception as e:
            logging.error(f"Logout Error: {e}")

    response = redirect(url_for('login.login'))

    using_ssl = (str(config.web_app_port) == "443") or (request.headers.get('X-Forwarded-Proto') == 'https')
    response.set_cookie(
        "session_id", 
        "", 
        expires=0, 
        httponly=True, 
        secure=using_ssl,
        samesite='Lax'
    )

    return response
