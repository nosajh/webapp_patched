from flask import Blueprint, render_template, request, logging
from app.database import get_db_connection

register_bp = Blueprint("register", __name__)

@register_bp.route("/register", methods=['GET', 'POST'])
@register_bp.route("/register.html", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            # --- ROLE VALIDATION (THE FIX) ---
            # We get the role from the form, but we strictly validate it.
            submitted_role = request.form.get('role', 'student').lower()

            # We ONLY allow 'student' or 'instructor'. 
            # If someone submits 'admin' or anything else, we force them to 'student'.
            if submitted_role in ['student', 'instructor']:
                role = submitted_role
            else:
                role = 'student'

            if not username or not password:
                return render_template('register.html', error="All fields are required.")

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if username exists
                    cur.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
                    if cur.fetchone()[0] > 0:
                        return render_template('register.html', error=f"'{username}' is already taken.")
                    
                    # Insert safely
                    cur.execute(
                        "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                        (username, password, role)
                    )
                    conn.commit()

            return render_template('register.html', success=f"User successfully created as {role}!")
            
        except Exception as e:
            logging.error(f"Registration Error: {e}")
            return render_template('register.html', error="An internal error occurred.")
        
    return render_template('register.html')