from flask import Blueprint, redirect, url_for, request
import logging
import config
from app.database import get_db_connection

logout_bp = Blueprint("logout", __name__)

@logout_bp.route('/logout')
@logout_bp.route('/logout.html')
def logout():
    # Get the session ID from the user's browser
    session_id = request.cookies.get("session_id")

    if session_id:
        try:
            # FIXED: Server-Side Invalidation. 
            # We must delete the session from the database so a hacker 
            # cannot "replay" the old cookie.
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
                    conn.commit()
        except Exception as e:
            logging.error(f"Error during logout database cleanup: {e}")

    # Prepare the redirect to the login page
    response = redirect(url_for('login.login'))

    # FIXED: Clear the cookie with the same flags used in login.py.
    # This ensures the browser properly deletes the "httponly" cookie.
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