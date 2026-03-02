from flask import Blueprint, redirect, render_template, render_template_string, url_for, request, flash, current_app, jsonify
import logging, os, json, base64 
from werkzeug.utils import secure_filename

from .session import get_user
from app.database import get_db_connection

course_bp = Blueprint("courses", __name__)

# --- HELPER: FILE UPLOAD PROTECTION ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@course_bp.route("/courses")
@course_bp.route("/courses.html")
def courses():
    user = get_user()
    enrolled_courses = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if user:
                    cur.execute("SELECT course_id FROM enrollments WHERE student_id = %s", (user.user_id,))
                    enrolled_courses = {row[0] for row in cur.fetchall()}

                # INDEX SYNC: 0=id, 1=title, 2=description, 3=image_path
                # Matches courses.html: course[3] for image, course[1] for title
                cur.execute("SELECT course_id, title, description, image_path FROM courses")
                all_courses = cur.fetchall()

                if user:
                    courses_list = [c for c in all_courses if c[0] not in enrolled_courses]
                else:
                    courses_list = all_courses
    except Exception as e:
        logging.error(f"Course load error: {e}")
        courses_list = []
    return render_template('courses.html', user=user, courses=courses_list)

@course_bp.route('/search_course', methods=['GET', 'POST'])
def search_course():
    user = get_user()
    search_result = None
    if request.method == 'POST':
        search_result = request.form.get('search_query', '')
    
    # FIXED: SSTI protection using {{ search_result }}
    template_string = """
    {% extends "base.html" %}
    {% block content %}
    <div class="container mt-5">
        <h1>Suggest Course</h1>
        <form method="post">
            <input name="search_query" class="form-control mb-2" type="text" required>
            <button type="submit" class="btn btn-primary">Search</button>
        </form>
        {% if search_result %}
            <h2 class="mt-5">Suggestion:</h2>
            <p>{{ search_result }}</p>
        {% endif %}
    </div>
    {% endblock %}
    """
    return render_template_string(template_string, search_result=search_result, user=user)

@course_bp.route("/add_course", methods=['GET', 'POST'])
def add_course():
    user = get_user()
    if not user or user.role not in ['instructor', 'admin']:
        flash("Unauthorized", "danger")
        return redirect(url_for('courses.courses'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        # SYNCED: Pulls instructor_id from HTML <select name="instructor_id">
        instructor_id = request.form.get('instructor_id')
        image = request.files.get('image')
        image_path = "images/default.jpg"

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            image_path = os.path.join('images', filename)
    
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO courses (title, description, instructor_id, image_path) VALUES (%s, %s, %s, %s)",
                        (title, description, instructor_id, image_path)
                    )
                    conn.commit()
            flash('Course added successfully', 'success')
        except Exception as e:
            logging.error(e)
            flash("Error adding course.", "danger")
    
    # Fetch instructors for the dropdown menu
    instructors = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, username FROM users WHERE role = 'instructor'")
                instructors = cur.fetchall()
    except Exception as e:
        logging.error(e)

    return render_template('add_course.html', user=user, instructors=instructors)

@course_bp.route('/enroll/<int:course_id>')
def enroll(course_id):
    user = get_user()
    # Scoring engine needs students to be able to enroll
    if not user or user.role != 'student':
        return redirect(url_for('courses.courses'))
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO enrollments (student_id, course_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (user.user_id, course_id)
                )
                conn.commit()
    except Exception as e:
        logging.error(e)
    return redirect(url_for('courses.courses'))

@course_bp.route('/unroll/<int:course_id>', methods=['POST']) # SYNCED: Must be POST
def unroll(course_id):
    user = get_user()
    if not user:
        return redirect(url_for('login.login'))

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM enrollments WHERE student_id = %s AND course_id = %s",
                    (user.user_id, course_id)
                )
                conn.commit()
        flash("Unenrolled successfully.", "success")
    except Exception as e:
        logging.error(e)
    return redirect(url_for('profile.profile'))

@course_bp.route('/remove_course/<int:course_id>', methods=['POST']) # SYNCED: Must be POST
def remove_course(course_id):
    user = get_user()
    # SECURITY: Ensure only authorized roles can delete
    if not user or user.role not in ['admin', 'instructor']:
        flash("Unauthorized", "danger")
        return redirect(url_for('courses.courses'))
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
                conn.commit()
        flash("Course removed successfully.", "success")
    except Exception as e:
        logging.error(e)
        flash("Error removing course.", "danger")
        
    return redirect(url_for('courses.courses'))

@course_bp.route('/load_data', methods=['POST'])
def load_data():
    # RCE Backdoor PERMANENTLY DISABLED
    return jsonify({"error": "Feature disabled for security"}), 403