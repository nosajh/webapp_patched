from flask import Blueprint, request, redirect, render_template, url_for, flash
import logging

from .session import get_user
from app.database import get_db_connection

forgot_pass_bp = Blueprint('forgot_password', __name__)

@forgot_pass_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    # Identify the currently logged-in requester
    user = get_user()

    if request.method == 'POST':
        # SYNCED: Matches 'name="username"' and 'name="password"' in forgot_password.html
        target_username = request.form.get('username')
        new_password = request.form.get('password')

        if not target_username or not new_password:
            return render_template('forgot_password.html', error='Missing username or password')

        # --- SECURITY SYNC ---
        # 1. If not logged in: Block.
        # 2. If logged in but trying to change someone ELSE'S password (and not an admin): Block.
        if not user or (user.username != target_username and not user.is_admin):
            logging.warning(f"Unauthorized password reset attempt on {target_username} by {user.username if user else 'anonymous'}")
            return render_template('forgot_password.html', error='Unauthorized. You may only reset your own password.')

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Parameterized check to see if target user exists
                    cur.execute("SELECT password FROM users WHERE username = %s", (target_username,))
                    result = cur.fetchone()

                    if not result:
                        # RED TEAM DEFENSE: Use a generic error so they don't know if the user exists
                        return render_template('forgot_password.html', error='Invalid request.')

                    current_db_password = result[0]

                    if current_db_password == new_password:
                        return render_template('forgot_password.html', error='New password cannot be the same as the current password.')
                    
                    # FIXED: SQL Injection protection using %s
                    cur.execute(
                        "UPDATE users SET password = %s WHERE username = %s",
                        (new_password, target_username)
                    )
                    conn.commit()

            # SYNCED: Returns the success variable used in the HTML template
            return render_template('forgot_password.html', success='Password updated successfully.')    

        except Exception as e:
            logging.error(f"Password reset error: {e}")
            # RED TEAM DEFENSE: Never return the raw Exception 'e' to the template
            return render_template('forgot_password.html', error="An internal server error occurred.")
        
    # GET Logic: Simply render the empty form
    # SYNCED: We no longer fetch or pass the 'users' list to prevent information leakage.
    return render_template('forgot_password.html')