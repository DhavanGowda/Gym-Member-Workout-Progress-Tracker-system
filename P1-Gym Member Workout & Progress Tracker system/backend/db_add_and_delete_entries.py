import mysql.connector
from contextlib import contextmanager
import logging

from logger_setup import setup_logger

logger=setup_logger('db_add_and_delete_entries','add_and_delete.log')

@contextmanager
def connect(commit=False):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",#Your username
        password="root", #your password
        database="gym_member",#the database schema is given you should add the entries to the table
    )
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            conn.commit()
    finally:
        cursor.close()
        conn.close()

# -------------------
# Members
# -------------------
def add_member(name, age, gender, joined_date, phone=None, email=None,username=None,password=None,role=None):
    with connect(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO members (name, age, gender, joined_date, phone, email,username,password,role) VALUES (%s, %s, %s, %s, %s, %s,%s,%s)",
            (name, age, gender, joined_date, phone, email,username,password,role),
        )
        last = cursor.lastrowid
        logger.info(f"Added member id={last} name={name}")
        return last

def create_member_with_credentials(name, age, gender, joined_date, phone, email, username, hashed_password, role='member'):
    with connect(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO members (name, age, gender, joined_date, phone, email, username, password, role) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (name, age, gender, joined_date, phone, email, username, hashed_password, role),
        )
        last = cursor.lastrowid
        logger.info(f"Created user id={last} username={username} role={role}")
        return last

def set_member_credentials(member_id, username, hashed_password, role='member'):
    with connect(commit=True) as cursor:
        cursor.execute(
            "UPDATE members SET username=%s, password=%s, role=%s WHERE id=%s",
            (username, hashed_password, role, member_id)
        )
        logger.info(f"Set credentials for member_id={member_id} username={username} role={role}")
        return cursor.rowcount

def update_member(member_id, name=None, age=None, gender=None, joined_date=None, phone=None, email=None,username=None,password=None,role=None):
    fields = []
    vals = []
    if name is not None:
        fields.append("name=%s"); vals.append(name)
    if age is not None:
        fields.append("age=%s"); vals.append(age)
    if gender is not None:
        fields.append("gender=%s"); vals.append(gender)
    if joined_date is not None:
        fields.append("joined_date=%s"); vals.append(joined_date)
    if phone is not None:
        fields.append("phone=%s"); vals.append(phone)
    if email is not None:
        fields.append("email=%s"); vals.append(email)
    if username is not None:
        fields.append("username=%s"); vals.append(username)
    if password is not None:
        fields.append("password=%s");vals.append(password)
    if role is not None:
        fields.append("role=%s");vals.append(role)

    if not fields:
        return 0
    vals.append(member_id)
    sql = f"UPDATE members SET {', '.join(fields)} WHERE id=%s"
    with connect(commit=True) as cursor:
        cursor.execute(sql, tuple(vals))
        logger.info(f"Updated member id={member_id} fields={fields}")
        return cursor.rowcount

def delete_member(member_id):
    with connect(commit=True) as cursor:
        cursor.execute("DELETE FROM members WHERE id = %s", (member_id,))
        logger.info(f"Deleted member id={member_id}")
        return cursor.rowcount

# Exercises
def add_exercise(name, muscle_group=None, equipment=None):
    with connect(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO exercises (name, muscle_group, equipment) VALUES (%s, %s, %s)",
            (name, muscle_group, equipment),
        )
        last = cursor.lastrowid
        logger.info(f"Added exercise id={last} name={name}")
        return last

def update_exercise(exercise_id, name=None, muscle_group=None, equipment=None):
    fields = []; vals = []
    if name is not None:
        fields.append("name=%s"); vals.append(name)
    if muscle_group is not None:
        fields.append("muscle_group=%s"); vals.append(muscle_group)
    if equipment is not None:
        fields.append("equipment=%s"); vals.append(equipment)
    if not fields:
        return 0
    vals.append(exercise_id)
    sql = f"UPDATE exercises SET {', '.join(fields)} WHERE id=%s"
    with connect(commit=True) as cursor:
        cursor.execute(sql, tuple(vals))
        logger.info(f"Updated exercise id={exercise_id}")
        return cursor.rowcount

def delete_exercise(exercise_id):
    with connect(commit=True) as cursor:
        cursor.execute("DELETE FROM exercises WHERE id = %s", (exercise_id,))
        logger.info(f"Deleted exercise id={exercise_id}")
        return cursor.rowcount

# Workout Sessions
def add_workout_session(member_id, session_date, total_duration=None, notes=None):
    with connect(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO workout_sessions (member_id, session_date, total_duration, notes) VALUES (%s, %s, %s, %s)",
            (member_id, session_date, total_duration, notes),
        )
        last = cursor.lastrowid
        logger.info(f"Added session id={last} member_id={member_id} date={session_date}")
        return last

def update_workout_session(session_id, session_date=None, total_duration=None, notes=None):
    fields=[]; vals=[]
    if session_date is not None:
        fields.append("session_date=%s"); vals.append(session_date)
    if total_duration is not None:
        fields.append("total_duration=%s"); vals.append(total_duration)
    if notes is not None:
        fields.append("notes=%s"); vals.append(notes)
    if not fields:
        return 0
    vals.append(session_id)
    sql = f"UPDATE workout_sessions SET {', '.join(fields)} WHERE id=%s"
    with connect(commit=True) as cursor:
        cursor.execute(sql, tuple(vals))
        logger.info(f"Updated session id={session_id}")
        return cursor.rowcount

def delete_workout_session(session_id):
    with connect(commit=True) as cursor:
        cursor.execute("DELETE FROM workout_logs WHERE session_id = %s", (session_id,))
        cursor.execute("DELETE FROM workout_sessions WHERE id = %s", (session_id,))
        logger.info(f"Deleted session id={session_id}")
        return cursor.rowcount

# Workout Logs
def add_workout_log(session_id, exercise_id, sets, reps, weight=None, calories_burned=None):
    with connect(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO workout_logs (session_id, exercise_id, sets, reps, weight, calories_burned) VALUES (%s, %s, %s, %s, %s, %s)",
            (session_id, exercise_id, sets, reps, weight, calories_burned),
        )
        last = cursor.lastrowid
        logger.info(f"Added log id={last} session_id={session_id} exercise_id={exercise_id}")
        return last

def update_workout_log(log_id, session_id=None, exercise_id=None, sets=None, reps=None, weight=None, calories_burned=None):
    fields=[]; vals=[]
    if session_id is not None:
        fields.append("session_id=%s"); vals.append(session_id)
    if exercise_id is not None:
        fields.append("exercise_id=%s"); vals.append(exercise_id)
    if sets is not None:
        fields.append("sets=%s"); vals.append(sets)
    if reps is not None:
        fields.append("reps=%s"); vals.append(reps)
    if weight is not None:
        fields.append("weight=%s"); vals.append(weight)
    if calories_burned is not None:
        fields.append("calories_burned=%s"); vals.append(calories_burned)
    if not fields:
        return 0
    vals.append(log_id)
    sql = f"UPDATE workout_logs SET {', '.join(fields)} WHERE id=%s"
    with connect(commit=True) as cursor:
        cursor.execute(sql, tuple(vals))
        logger.info(f"Updated log id={log_id}")
        return cursor.rowcount

def delete_workout_log(log_id):
    with connect(commit=True) as cursor:
        cursor.execute("DELETE FROM workout_logs WHERE id = %s", (log_id,))
        logger.info(f"Deleted log id={log_id}")
        return cursor.rowcount

# Body Measurements
def add_body_measurement(member_id, measure_date, weight=None, chest=None, arms=None, waist=None, notes=None):
    with connect(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO body_measurements (member_id, measure_date, weight, chest, arms, waist, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (member_id, measure_date, weight, chest, arms, waist, notes),
        )
        last = cursor.lastrowid
        logger.info(f"Added measurement id={last} member_id={member_id}")
        return last

def update_body_measurement(measure_id, measure_date=None, weight=None, chest=None, arms=None, waist=None, notes=None):
    fields=[]; vals=[]
    if measure_date is not None:
        fields.append("measure_date=%s"); vals.append(measure_date)
    if weight is not None:
        fields.append("weight=%s"); vals.append(weight)
    if chest is not None:
        fields.append("chest=%s"); vals.append(chest)
    if arms is not None:
        fields.append("arms=%s"); vals.append(arms)
    if waist is not None:
        fields.append("waist=%s"); vals.append(waist)
    if notes is not None:
        fields.append("notes=%s"); vals.append(notes)
    if not fields:
        return 0
    vals.append(measure_id)
    sql = f"UPDATE body_measurements SET {', '.join(fields)} WHERE id=%s"
    with connect(commit=True) as cursor:
        cursor.execute(sql, tuple(vals))
        logger.info(f"Updated measurement id={measure_id}")
        return cursor.rowcount

def delete_body_measurement(measure_id):
    with connect(commit=True) as cursor:
        cursor.execute("DELETE FROM body_measurements WHERE id = %s", (measure_id,))
        logger.info(f"Deleted measurement id={measure_id}")
        return cursor.rowcount
