import logging
import psycopg2
import random
from .connection import get_db_connection

def create_tables():
    # 1. TABLE SCHEMAS
    table_schemas = [
        "CREATE TABLE IF NOT EXISTS users (user_id SERIAL PRIMARY KEY, username VARCHAR(32) UNIQUE NOT NULL, password VARCHAR(32) NOT NULL, role VARCHAR(20) CHECK (role IN ('student', 'instructor', 'admin')) NOT NULL)",
        "CREATE TABLE IF NOT EXISTS sessions (session_id CHAR(32) PRIMARY KEY, user_id INTEGER NOT NULL, expiration TIMESTAMP NOT NULL, FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE)",
        "CREATE TABLE IF NOT EXISTS courses (course_id SERIAL PRIMARY KEY, title VARCHAR(100) NOT NULL UNIQUE, description TEXT, instructor_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL, image_path VARCHAR(255))",
        "CREATE TABLE IF NOT EXISTS enrollments (enrollment_id SERIAL PRIMARY KEY, student_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE, course_id INTEGER REFERENCES courses(course_id) ON DELETE CASCADE, UNIQUE (student_id, course_id))"
    ]

    # 2. FULL SEED DATA (Restored from original.txt)
    seed_users = [
        ('admin', 'admin123', 'admin'),
        ('student1', 'password1', 'student'),
        ('student2', 'password2', 'student'),
        ('student3', 'password3', 'student'),
        ('instructor1', 'instructorpass1', 'instructor'),
        ('instructor2', 'instructorpass2', 'instructor'),
        ('instructor3', 'instructorpass3', 'instructor')
    ]

    seed_courses = [
        ('Intro to Cybersecurity', 'Welcome to Introduction to Cybersecurity, an essential course designed for individuals new to the field of cybersecurity. This course provides a foundational understanding of key concepts and practices critical to protecting digital information and systems from threats and vulnerabilities.', 'images/intro.jpg'),
        ('Ethical Hacking and Penetration Testing', 'Explore the techniques and tools used by ethical hackers to identify and exploit vulnerabilities in systems, networks, and applications. Learn about penetration testing methodologies, vulnerability assessment, and how to ethically simulate attacks to enhance security.', 'images/hacking.jpg'),
        ('Incident Response and Management', 'Learn how to effectively respond to and manage cybersecurity incidents. Topics include incident detection, analysis, containment, eradication, and recovery, as well as creating and implementing an incident response plan.', 'images/incident.jpg'),
        ('Malware Analysis', 'Delve into the techniques used to analyze and understand malware. This course covers malware types, reverse engineering, and how to detect and mitigate malware threats.', 'images/malware.jpg'),
        ('Cybersecurity for IoT Devices', 'Focus on the unique security challenges posed by Internet of Things (IoT) devices. This course covers vulnerabilities, attack vectors, and best practices for securing IoT environments and devices.', 'images/iot.jpg'),
        ('Cloud Security', 'This course provides a foundational understanding of securing cloud environments, focusing on cloud architecture, security controls, and compliance. You will learn to identify and mitigate cloud-specific threats, implement security best practices for cloud services, and manage risks associated with cloud computing.', 'images/cloud.jpg'),
        ('Advanced Threat Hunting', 'Master advanced techniques for identifying and mitigating sophisticated cyber threats. This course covers the latest tools and methodologies for proactive threat detection and response.', 'images/threat_hunting.jpg'),
        ('Introduction to Programming with Python', 'Start your programming journey with Python, one of the most popular and versatile programming languages. Learn basic programming concepts and problem-solving techniques.', 'images/python.jpg')
    ]

    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()

        # Create Tables
        for schema in table_schemas:
            cur.execute(schema)

        # Insert/Reset Users (DO UPDATE ensures admin123 is always restored)
        for user in seed_users:
            cur.execute("""
                INSERT INTO users (username, password, role) VALUES (%s, %s, %s)
                ON CONFLICT (username) 
                DO UPDATE SET password = EXCLUDED.password, role = EXCLUDED.role
            """, user)

        # Insert/Reset Courses (Restores full descriptions if deleted/modified)
        for course in seed_courses:
            cur.execute("""
                INSERT INTO courses (title, description, image_path) VALUES (%s, %s, %s)
                ON CONFLICT (title) 
                DO UPDATE SET description = EXCLUDED.description, image_path = EXCLUDED.image_path
            """, course)

        conn.commit()

        # 3. DYNAMIC ASSIGNMENT LOGIC
        cur.execute("SELECT user_id FROM users WHERE role = 'instructor'")
        instructor_ids = [row[0] for row in cur.fetchall()]
        
        cur.execute("SELECT course_id FROM courses")
        course_ids = [row[0] for row in cur.fetchall()]

        if instructor_ids and course_ids:
            for c_id in course_ids:
                cur.execute("UPDATE courses SET instructor_id = %s WHERE course_id = %s", 
                           (random.choice(instructor_ids), c_id))

        cur.execute("SELECT user_id FROM users WHERE role = 'student'")
        student_ids = [row[0] for row in cur.fetchall()]

        if student_ids and course_ids:
            for s_id in student_ids:
                # Assign 2 random courses per student
                target_courses = random.sample(course_ids, min(2, len(course_ids)))
                for c_id in target_courses:
                    # FIXED: Proper parameterized query for enrollments
                    cur.execute("""
                        INSERT INTO enrollments (student_id, course_id) 
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                    """, (s_id, c_id))
            
        conn.commit()
        cur.close()
        logging.info("Database setup and seeding completed successfully.")
        
    except Exception as e:
        logging.error(f"Database Setup Error: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
