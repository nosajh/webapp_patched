import psycopg2
import config
import logging

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=config.db_host,
            port=config.db_port,
            database=config.db_name,
            user=config.db_user,
            password=config.db_password,
            # FIXED: Added a 5-second timeout. 
            # If the .7 VM is down, the app won't hang the scoring script.
            connect_timeout=5 
        )
        return conn
    except Exception as e:
        logging.error(f"Could not connect to Database at {config.db_host}: {e}")
        return None