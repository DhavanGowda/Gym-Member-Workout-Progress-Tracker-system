import mysql.connector
from contextlib import contextmanager
import logging
from logger_setup import setup_logger

logger=setup_logger('df_get_info','info.log')

@contextmanager
def connect(commit=False):
    conn = mysql.connector.connect(
        host="localhost",
        user="root", #Your username
        password="root", #your password
        database="gym_member", #the database schema is given you should add the entries to the table
    )
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            conn.commit()
    finally:
        cursor.close()
        conn.close()

# Members (reads)
def get_all_members(limit=1000, offset=0):
    with connect() as cursor:
        cursor.execute("SELECT * FROM members ORDER BY id ASC LIMIT %s OFFSET %s", (limit, offset))
        logger.info("All members info fetched")
        return cursor.fetchall()

def get_member_by_id(member_id):
    with connect() as cursor:
        cursor.execute("SELECT * FROM members WHERE id=%s", (member_id,))
        return cursor.fetchone()

def get_members_by_gender(gender):
    with connect() as cursor:
        cursor.execute("SELECT * FROM members WHERE gender=%s ORDER BY id ASC", (gender,))
        return cursor.fetchall()

def get_members_by_name(name):
    with connect() as cursor:
        cursor.execute("SELECT * FROM members WHERE name LIKE %s ORDER BY id ASC", (f"%{name}%",))
        return cursor.fetchall()

def get_member_by_username(username):
    with connect() as cursor:
        cursor.execute("SELECT * FROM members WHERE username=%s", (username,))
        return cursor.fetchone()

def count_members():
    with connect() as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM members")
        return cursor.fetchone()["cnt"]

# Exercises
def get_all_exercises(limit=500):
    with connect() as cursor:
        cursor.execute("SELECT * FROM exercises ORDER BY id ASC LIMIT %s", (limit,))
        logger.info("All exercises info fetched")
        return cursor.fetchall()

def get_exercise_by_id(exercise_id):
    with connect() as cursor:
        cursor.execute("SELECT * FROM exercises WHERE id=%s", (exercise_id,))
        return cursor.fetchone()

# Sessions
def get_session_by_id(session_id):
    with connect() as cursor:
        cursor.execute("SELECT * FROM workout_sessions WHERE id=%s", (session_id,))
        return cursor.fetchone()

def get_sessions_for_member(member_id, start_date=None, end_date=None):
    sql = "SELECT * FROM workout_sessions WHERE member_id=%s"
    params = [member_id]
    if start_date:
        sql += " AND session_date >= %s"; params.append(start_date)
    if end_date:
        sql += " AND session_date <= %s"; params.append(end_date)
    sql += " ORDER BY session_date DESC"
    with connect() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

def get_recent_sessions(limit=20):
    with connect() as cursor:
        cursor.execute("SELECT * FROM workout_sessions ORDER BY session_date DESC LIMIT %s", (limit,))
        return cursor.fetchall()

# Logs
def get_log_by_id(log_id):
    with connect() as cursor:
        cursor.execute("SELECT * FROM workout_logs WHERE id=%s", (log_id,))
        return cursor.fetchone()

def get_logs_for_session(session_id):
    with connect() as cursor:
        cursor.execute("SELECT wl.*, e.name AS exercise_name FROM workout_logs wl LEFT JOIN exercises e ON wl.exercise_id = e.id WHERE wl.session_id=%s", (session_id,))
        return cursor.fetchall()

def get_logs_for_member(member_id, start_date=None, end_date=None):
    sql = """
    SELECT wl.*, ws.session_date, e.name as exercise_name
    FROM workout_logs wl
    JOIN workout_sessions ws ON wl.session_id = ws.id
    LEFT JOIN exercises e ON wl.exercise_id = e.id
    WHERE ws.member_id=%s
    """
    params = [member_id]
    if start_date:
        sql += " AND ws.session_date >= %s"; params.append(start_date)
    if end_date:
        sql += " AND ws.session_date <= %s"; params.append(end_date)
    sql += " ORDER BY ws.session_date DESC"
    with connect() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

# Measurements
def get_measurements_for_member(member_id, start_date=None, end_date=None):
    sql = "SELECT * FROM body_measurements WHERE member_id=%s"
    params = [member_id]
    if start_date:
        sql += " AND measure_date >= %s"; params.append(start_date)
    if end_date:
        sql += " AND measure_date <= %s"; params.append(end_date)
    sql += " ORDER BY measure_date ASC"
    with connect() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

def get_measurement_by_id(measure_id):
    with connect() as cursor:
        cursor.execute("SELECT * FROM body_measurements WHERE id=%s", (measure_id,))
        return cursor.fetchone()

#useful for authentication
def set_member_credentials(member_id, username, hashed_password, role='member'):
    with connect(commit=True) as cursor:
        cursor.execute(
            "UPDATE members SET username=%s, password=%s, role=%s WHERE id=%s",
            (username, hashed_password, role, member_id)
        )
        logger.info(f"Set credentials for member_id={member_id} username={username} role={role}")
        return cursor.rowcount

def create_member_with_credentials(name, age, gender, joined_date, phone, email, username, hashed_password, role='member'):
    with connect(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO members (name, age, gender, joined_date, phone, email, username, password, role) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (name, age, gender, joined_date, phone, email, username, hashed_password, role),
        )
        last = cursor.lastrowid
        logger.info(f"Created user id={last} username={username} role={role}")
        return last

# Useful joins / analytics helpers
def get_member_sessions_with_logs(member_id, start_date=None, end_date=None):
    sql = """
    SELECT ws.id as session_id, ws.session_date, ws.total_duration, ws.notes,
           wl.id as log_id, wl.exercise_id, e.name as exercise_name, wl.sets, wl.reps, wl.weight, wl.calories_burned
    FROM workout_sessions ws
    LEFT JOIN workout_logs wl ON wl.session_id = ws.id
    LEFT JOIN exercises e ON wl.exercise_id = e.id
    WHERE ws.member_id = %s
    """
    params = [member_id]
    if start_date:
        sql += " AND ws.session_date >= %s"; params.append(start_date)
    if end_date:
        sql += " AND ws.session_date <= %s"; params.append(end_date)
    sql += " ORDER BY ws.session_date DESC, wl.id ASC"
    with connect() as cursor:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

def get_top_exercises_for_member(member_id, limit=10):
    sql = """
    SELECT e.id AS exercise_id, e.name AS exercise_name, COUNT(*) AS times_performed,
           SUM(wl.sets * wl.reps) AS total_reps, SUM(IFNULL(wl.weight,0) * wl.sets * wl.reps) AS total_lift
    FROM workout_logs wl
    JOIN workout_sessions ws ON wl.session_id = ws.id
    JOIN exercises e ON wl.exercise_id = e.id
    WHERE ws.member_id = %s
    GROUP BY e.id, e.name
    ORDER BY times_performed DESC
    LIMIT %s
    """
    with connect() as cursor:
        cursor.execute(sql, (member_id, limit))
        logger.info(f"Top exercises for member id={member_id} limit=%s")
        return cursor.fetchall()

def raw_query(sql, params=None):
    with connect() as cursor:
        cursor.execute(sql, params or ())
        try:
            return cursor.fetchall()
        except:
            return None
