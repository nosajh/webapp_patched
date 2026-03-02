from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from .session import get_user
import logging
import os
from werkzeug.utils import secure_filename 
from app.database import get_db_connection

profile_bp = Blueprint("profile", __name__)

@profile_bp.route('/profile', methods=['GET'])
def profile():
    user = get_user()
    if user is None:
        return redirect(url_for('login.login'))

    courses = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # SYNCED INDEX ORDER: 0=ID, 1=Title, 2=Description, 3=Image_Path
                if user.role == 'instructor':
                    cur.execute("""
                        SELECT c.course_id, c.title, c.description, c.image_path
                        FROM courses c
                        JOIN users u ON c.instructor_id = u.user_id
                        WHERE u.username = %s
                    """, (user.username,))
                else:
                    cur.execute("""
                        SELECT c.course_id, c.title, c.description, c.image_path
                        FROM enrollments e
                        JOIN courses c ON e.course_id = c.course_id
                        JOIN users u ON e.student_id = u.user_id
                        WHERE u.username = %s
                    """, (user.username,))
                courses = cur.fetchall()
    except Exception as e:
        logging.error(f"Profile load error: {e}")

    return render_template('profile.html', user=user, courses=courses)

@profile_bp.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    user = get_user()
    if user is None:
        return redirect(url_for('login.login'))
    
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_password = request.form.get('password')

        if not new_username or not new_password:
            flash('Fields cannot be empty', 'danger')
            return redirect(url_for('profile.edit_profile'))

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # FIXED: SQL Injection protection using %s
                    cur.execute(
                        "UPDATE users SET username = %s, password = %s WHERE user_id = %s",
                        (new_username, new_password, user.user_id)
                    )
                    conn.commit()

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile.profile'))
        
        except Exception as e:
            logging.error(f"Profile update error: {e}")
            flash('An error occurred while updating profile', 'danger')

    return render_template('edit_profile.html', user=user)

@profile_bp.route('/upload', methods=['GET', 'POST'])
def upload_file():
    user = get_user()
    if user is None:
        return redirect(url_for('login.login'))
    
    # RED TEAM DEFENSE: Ensure upload dir exists
    upload_dir = os.path.join(current_app.root_path, 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename:
            filename = secure_filename(file.filename)
            
            # FIXED: Extension whitelist (Prevents .php, .py, .sh webshells)
            ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'txt', 'pdf'}
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            if ext not in ALLOWED_EXTENSIONS:
                flash('File type forbidden for security reasons.', 'danger')
                return redirect(url_for('profile.upload_file'))

            file.save(os.path.join(upload_dir, filename))
            flash('File uploaded successfully', 'success')
        else:
            flash('No file selected', 'danger')
        return redirect(url_for('profile.upload_file'))
    
    # List files for upload.html table
    uploaded_files = os.listdir(upload_dir) if os.path.exists(upload_dir) else []
    return render_template('upload.html', user=user, uploaded_files=uploaded_files)

@profile_bp.route('/run/<filename>', methods=['POST'])
def run_file(filename):
    # CRITICAL SECURITY FIX: Backdoor permanently disabled.
    # This prevents Red Teamers from triggering RCE even if they bypass the UI.
    flash('Arbitrary script execution is disabled on this server.', 'danger')
    return redirect(url_for('profile.upload_file'))

@profile_bp.route('/delete/<filename>', methods=['POST']) # SYNCED: Must be POST
def delete_file(filename):
    user = get_user()
    if user is None:
        return jsonify({"error": "Unauthorized"}), 403

    # RED TEAM DEFENSE: Path traversal protection
    filename = secure_filename(filename)
    upload_dir = os.path.join(current_app.root_path, 'uploads')
    file_path = os.path.join(upload_dir, filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('File deleted successfully', 'success')
        else:
            flash('File not found', 'danger')
    except Exception as e:
        logging.error(f"Delete error: {e}")
        flash('Internal error during deletion', 'danger')
    
    return redirect(url_for('profile.upload_file'))