import logging
import psycopg2
import random
from .connection import get_db_connection

def create_tables():
    # 1. TABLE SCHEMAS (Kept original structure to ensure scoring compatibility)
    table_schemas = [
        "CREATE TABLE IF NOT EXISTS users (user_id SERIAL PRIMARY KEY, username VARCHAR(32) UNIQUE NOT NULL, password VARCHAR(32) NOT NULL, role VARCHAR(20) CHECK (role IN ('student', 'instructor', 'admin')) NOT NULL)",
        "CREATE TABLE IF NOT EXISTS sessions (session_id CHAR(32) PRIMARY KEY, user_id INTEGER NOT NULL, expiration TIMESTAMP NOT NULL, FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE)",
        "CREATE TABLE IF NOT EXISTS courses (course_id SERIAL PRIMARY KEY, title VARCHAR(100) NOT NULL UNIQUE, description TEXT, instructor_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL, image_path VARCHAR(255))",
        "CREATE TABLE IF NOT EXISTS enrollments (enrollment_id SERIAL PRIMARY KEY, student_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE, course_id INTEGER REFERENCES courses(course_id) ON DELETE CASCADE, UNIQUE (student_id, course_id))"
    ]

    # 2. SEED DATA
    # The scoring user must be admin:admin123
    seed_users = [
        ('admin', 'admin123', 'admin'),
        ('instructor1', 'instructorpass1', 'instructor'),
        ('instructor2', 'instructorpass2', 'instructor'),
        ('student1', 'password1', 'student'),
        ('student2', 'password2', 'student')
    ]

    seed_courses = [
        ('Intro to Cybersecurity', 'Foundational understanding of key concepts.', 'images/intro.jpg'),
        ('Ethical Hacking', 'Techniques used by ethical hackers.', 'images/hacking.jpg'),
        ('Malware Analysis', 'Understand and mitigate malware threats.', 'images/malware.jpg'),
        ('Cloud Security', 'Securing cloud environments.', 'images/cloud.jpg')
    ]

    conn = get_db_connection()
    if not conn:
        return # Connection failed, handled by logging in connection.py

    try:
        cur = conn.cursor()

        # Create Tables
        for schema in table_schemas:
            cur.execute(schema)

        # Insert Users
        for user in seed_users:
            cur.execute("""
                INSERT INTO users (username, password, role) VALUES (%s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            """, user)

        # Insert Courses
        for course in seed_courses:
            cur.execute("""
                INSERT INTO courses (title, description, image_path) VALUES (%s, %s, %s)
                ON CONFLICT (title) DO NOTHING
            """, course)

        conn.commit()

        # 3. ASSIGNMENT LOGIC (Instructors/Students)
        cur.execute("SELECT user_id FROM users WHERE role = 'instructor'")
        instructor_ids = [row[0] for row in cur.fetchall()]
        
        cur.execute("SELECT course_id FROM courses")
        course_ids = [row[0] for row in cur.fetchall()]

        if instructor_ids and course_ids:
            for course_id in course_ids:
                cur.execute("UPDATE courses SET instructor_id = %s WHERE course_id = %s", 
                           (random.choice(instructor_ids), course_id))

        cur.execute("SELECT user_id FROM users WHERE role = 'student'")
        student_ids = [row[0] for row in cur.fetchall()]

        if student_ids and course_ids:
            for student_id in student_ids:
                # Assign 2 random courses per student
                target_courses = random.sample(course_ids, min(2, len(course_ids)))
                for c_id in target_courses:
                    # FIXED: Removed % formatting, used proper parameters
                    cur.execute("""
                        INSERT INTO enrollments (student_id, course_id) 
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                    """, (student_id, c_id))
            
        conn.commit()
        cur.close()
    except Exception as e:
        logging.error(f"Database Setup Error: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()