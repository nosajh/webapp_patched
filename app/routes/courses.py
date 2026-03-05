from flask import Blueprint, redirect, render_template, render_template_string, url_for, request, flash, current_app, jsonify
import logging, os, json, base64 
from werkzeug.utils import secure_filename

from .session import get_user
from app.database import get_db_connection

course_bp = Blueprint("courses", __name__)

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
        search_query = request.form.get('search_query', '')
        if not search_query:
            flash('Please enter a search query.', 'danger')
            return redirect(url_for('courses.search_course'))
        search_result = search_query
    
    template_string = """
    {% extends "base.html" %}

    {% block title %}Course Suggestions{% endblock %}

    {% block content %}
    <div class="container mt-5">
        {% with messages = get_flashed_messages(with_categories=True) %}
            {% if messages %}
                <div class="alert-container">
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        <h1>Suggest Course</h1>
        <form method="post" action="{{ url_for('courses.search_course') }}">
            <div class="form-group">
                <label for="search_query">Course Topic:</label>
                <input id="search_query" name="search_query" class="form-control" type="text" placeholder="Enter course topic..." required>
            </div>
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
        flash("Unauthorized access.", "danger")
        return redirect(url_for('courses.courses'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        instructor_id = request.form.get('instructor_id')
        image = request.files.get('image')
        image_path = "images/default.jpg"

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            image.save(upload_path)
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
            logging.error(f"Course creation failed: {e}")
            flash("Error: Title must be unique or database is unavailable.", "danger")
    
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
    if not user or user.role != 'student':
        flash("Only students can enroll in courses.", "warning")
        return redirect(url_for('courses.courses'))
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO enrollments (student_id, course_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (user.user_id, course_id)
                )
                conn.commit()
        flash("Successfully enrolled!", "success")
    except Exception as e:
        logging.error(f"Enrollment error: {e}")
    return redirect(url_for('courses.courses'))

@course_bp.route('/unroll/<int:course_id>', methods=['POST']) 
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
        flash("Successfully removed from course.", "success")
    except Exception as e:
        logging.error(f"Unroll error: {e}")
    return redirect(url_for('profile.profile'))

@course_bp.route('/remove_course/<int:course_id>', methods=['POST'])
def remove_course(course_id):
    user = get_user()
    if not user or user.role not in ['admin', 'instructor']:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('courses.courses'))
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
                conn.commit()
        flash("Course deleted.", "success")
    except Exception as e:
        logging.error(f"Course deletion error: {e}")
        flash("Error removing course.", "danger")
        
    return redirect(url_for('courses.courses'))

@course_bp.route('/load_data', methods=['POST'])
def load_data():
    return jsonify({"error": "Pickle deserialization is disabled for security."}), 403
