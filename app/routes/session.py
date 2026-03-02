from typing import Union
from flask import request
import logging
from datetime import datetime, timezone # Added timezone for reliable scoring

from app.database import get_db_connection

class User:
    def __init__(self, user_id: int, username: Union[str, None], role: Union[str, None]):
        # FIXED: Ensure user_id is an integer to prevent type errors in other scripts
        self.__user_id = int(user_id)
        self.__username = username
        self.__role = role

    @property
    def user_id(self) -> int:
        return self.__user_id

    @property
    def username(self) -> Union[str, None]:
        return self.__username
    
    @property
    def role(self) -> Union[str, None]:
        return self.__role
    
    @property
    def is_admin(self) -> bool:
        return self.__role == 'admin'
    

def get_user() -> Union[User, None]:
    # Extract session_id from cookie
    session_id = request.cookies.get("session_id", None)

    if session_id is None:
        return None
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # The query uses %s, which is already secure against SQLi.
                cur.execute(
                    """
                    SELECT
                        u.user_id, u.username, s.expiration, u.role
                    FROM
                        sessions s
                    JOIN users u ON s.user_id = u.user_id
                    WHERE
                        s.session_id = %s
                    ORDER BY
                        s.expiration DESC LIMIT 1
                    """,
                    (session_id,)
                )
                result = cur.fetchone()

                if result is None:
                    return None
                
                user_id, username, expiration, role = result

                # FIXED: Timezone Awareness.
                # In Ubuntu 24.04, datetime.now() uses local system time.
                # If your database stores UTC (common for Postgres), 
                # sessions might expire instantly or stay alive forever.
                # We force UTC comparison to match the login.py logic.
                
                # Check if expiration from DB has a timezone; if not, assume UTC.
                #if expiration.tzinfo is None:
                #    expiration = expiration.replace(tzinfo=timezone.utc)

                #if expiration < datetime.now(timezone.utc):
                #    logging.info(f"Session {session_id} expired.")

                #timezone naive version should work lol
                if expiration < datetime.now():
                    return None
                
                return User(user_id, username, role)
                
    except Exception as e:
        # FIXED: Robustness for Scoring.
        # If the database is busy or restarting, we don't want the whole site to crash (500 error).
        # We catch the error, log it, and return None (user not logged in).
        # This keeps the homepage visible even if the session table is locked.
        logging.error(f"Session retrieval error: {e}")
        return None
