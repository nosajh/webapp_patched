from flask import Blueprint, redirect, render_template, render_template_string, url_for, request, flash, current_app, jsonify
import logging, os, json, base64 
from werkzeug.utils import secure_filename

from .session import get_user
from app.database import get_db_connection

course_bp = Blueprint("courses", __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        <!-- Display Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=True) %}
            {% if messages %}
                <div class="alert-container">
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">
                            {{ message }}
                        </div>
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

# ... (add_course, enroll, unroll, and remove_course remain exactly as we patched/synced them previously) ...
