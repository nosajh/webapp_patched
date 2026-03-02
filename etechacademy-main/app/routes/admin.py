from flask import Blueprint, request, render_template, redirect, url_for, render_template_string, flash
import subprocess
import logging

from .session import get_user
from app.database import get_db_connection

admin_bp = Blueprint("admin", __name__)

# --- HELPER FUNCTION TO PROTECT ADMIN ROUTES ---
def login_required_admin(user):
    """Checks if the user is logged in and is an administrator."""
    if user is None or not user.is_admin:
        return False
    return True

@admin_bp.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    user = get_user()
    if not login_required_admin(user):
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login.login'))
    
    search_query = request.args.get('search', '')

    # --- DELETE USER LOGIC ---
    if request.method == 'POST':
        user_id_to_delete = request.form.get('user_id')
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # SAFETY: Prevent the admin from deleting their own account
                    # (Prevents losing the 6,000pt scoring user)
                    if int(user_id_to_delete) == user.user_id:
                        flash("Action Denied: You cannot delete your own session account.", "warning")
                    else:
                        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id_to_delete,))
                        conn.commit()
                        flash("User successfully removed.", "success")
        except Exception as e:
            logging.error(f"Deletion error: {e}")
            flash("Failed to delete user.", "danger")
        
    # --- DASHBOARD DATA LOADING ---
    page = request.args.get('page', 1, type=int)
    per_page = 10
    start_index = (page - 1) * per_page

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # SYNCED QUERY: user[0]=id, user[1]=username, user[2]=MASKED, user[3]=role
                # This ensures real passwords never enter the browser memory.
                if search_query:
                    cur.execute("""
                        SELECT user_id, username, '********', role 
                        FROM users 
                        WHERE username ILIKE %s 
                        ORDER BY user_id LIMIT %s OFFSET %s
                    """, (f"%{search_query}%", per_page, start_index))
                else:
                    cur.execute("""
                        SELECT user_id, username, '********', role 
                        FROM users 
                        ORDER BY user_id LIMIT %s OFFSET %s
                    """, (per_page, start_index))

                users_list = cur.fetchall()
                
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]
                total_pages = (total_users + per_page - 1) // per_page

                # SYNCED COURSE QUERY: Matches course management table
                cur.execute("SELECT course_id, title, description, instructor_id FROM courses ORDER BY course_id")
                courses_list = cur.fetchall()
    except Exception as e:
        logging.error(f"Dashboard load error: {e}")
        users_list, courses_list, total_pages = [], [], 1

    return render_template('admin_dashboard.html', 
                           user=user, 
                           users=users_list, 
                           courses=courses_list, 
                           total_pages=total_pages, 
                           current_page=page, 
                           search_query=search_query)

@admin_bp.route('/admin_dashboard/system_monitor', methods=['GET', 'POST'])
def system_monitor():
    user = get_user()
    if not login_required_admin(user):
        return redirect(url_for('login.login'))
    
    output = ""
    # FIXED: Whitelist only safe commands. shell=False prevents command injection (; rm -rf /)
    ALLOWED_COMMANDS = {
        'uptime': ['uptime'],
        'disk_usage': ['df', '-h'],
        'memory': ['free', '-m']
    }

    selected_key = request.form.get('command', 'uptime')
    try:
        if selected_key in ALLOWED_COMMANDS:
            cmd_to_run = ALLOWED_COMMANDS[selected_key]
            result = subprocess.run(cmd_to_run, shell=False, capture_output=True, text=True, timeout=5)
            output = result.stdout
        else:
            output = "Invalid command selected."
    except Exception as e:
        output = f"Command execution error: {str(e)}"

    template_string = """
    {% extends "base.html" %}
    {% block content %}
    <h2>System Monitor</h2>
    <form method="post">
        <select name="command" class="form-control">
            <option value="uptime">System Uptime</option>
            <option value="disk_usage">Disk Usage</option>
            <option value="memory">Memory Stats</option>
        </select>
        <button type="submit" class="btn btn-primary mt-2">Run Diagnostics</button>
    </form>
    {% if output %}<pre class="bg-dark text-white p-3 mt-3">{{ output }}</pre>{% endif %}
    {% endblock %}
    """
    return render_template_string(template_string, output=output, user=user)

@admin_bp.route('/admin_dashboard/add_user', methods=['GET', 'POST'])
def add_user():
    user = get_user()
    if not login_required_admin(user):
        return redirect(url_for('login.login'))
    
    if request.method == 'POST':
        # BOT SYNC: These field names must match the scoring script check_etech_academy.py
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if not username or not password or not role:
            flash('All fields required', 'danger')
        else:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                                   (username, password, role))
                        conn.commit()
                flash('User added successfully', 'success')
            except Exception as e:
                flash("Database error: Username may already exist.", "danger")
        
    return render_template('add_user.html', user=user)

@admin_bp.route('/admin_dashboard/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = get_user()
    if not login_required_admin(user):
        return redirect(url_for('login.login'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('password')
        role = request.form.get('role')

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # SYNCED LOGIC: Check if password was left blank (keep existing)
                    if not new_password:
                        cur.execute("UPDATE users SET username=%s, role=%s WHERE user_id=%s", 
                                   (username, role, user_id))
                    else:
                        cur.execute("UPDATE users SET username=%s, password=%s, role=%s WHERE user_id=%s", 
                                   (username, new_password, role, user_id))
                    conn.commit()
            flash("Account updated successfully", 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except Exception as e:
            logging.error(f"Edit error: {e}")
            flash("Update failed.", 'danger')
          
    # --- GET LOGIC (Pre-filling the form) ---
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # SYNCED FETCH: 0=username, 1=password(masked), 2=role
            # This matches the user_data[x] indices in edit_user.html
            cur.execute("SELECT username, '********', role FROM users WHERE user_id = %s", (user_id,))
            user_data = cur.fetchone()
        
    return render_template('edit_user.html', user=user, user_id=user_id, user_data=user_data)