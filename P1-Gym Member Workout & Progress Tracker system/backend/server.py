import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, status, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
import pandas as pd


import db_add_and_delete_entries
import db_get_info

# -----------------------
# Basic config / logging
# -----------------------

from logger_setup import setup_logger

logger=setup_logger('server','server.log')

app = FastAPI(title="Gym Member Tracker (tokenless auth, dev)")

# Allow Streamlit frontend origins (adjust if needed)
origins = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------
# Pydantic models
# -----------------
class MemberInfoIn(BaseModel):
    name: str
    age: int
    gender: str
    joined_date: datetime
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    username:str=None
    password:str=None


class SessionCreate(BaseModel):
    member_id: int
    session_date: datetime
    total_duration: Optional[int] = None
    notes: Optional[str] = None

class LogCreate(BaseModel):
    session_id: int
    exercise_id: int
    sets: int
    reps: int
    weight: Optional[float] = None
    calories_burned: Optional[float] = None

class MeasurementCreate(BaseModel):
    member_id: int
    measure_date: datetime
    weight: Optional[float] = None
    chest: Optional[float] = None
    arms: Optional[float] = None
    waist: Optional[float] = None
    notes: Optional[str] = None

class LoginIn(BaseModel):
    username: str
    password: str

# -----------------
# Simple auth helpers (plain-text, DEV only)
# -----------------
def verify_password_plain(plain: str, stored: Optional[str]) -> bool:
    if stored is None:
        return False
    return plain == stored

def fetch_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    return db_get_info.get_member_by_username(username)

# -----------------
# get_current_user dependency (tokenless)
# -----------------
async def get_current_user(request: Request):

    username = None
    password = None

    # 1) headers
    username = request.headers.get("X-Username")
    password = request.headers.get("X-Password")

    # 2) json auth block (only attempt if not both present)
    if (not username or not password) and request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                auth_block = body.get("auth")
                if isinstance(auth_block, dict):
                    username = username or auth_block.get("username")
                    password = password or auth_block.get("password")
        except Exception:
            # body might be empty or not JSON — ignore
            pass

    # 3) query params fallback
    if not username or not password:
        q = request.query_params
        username = username or q.get("username")
        password = password or q.get("password")

    if not username or not password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")

    user = fetch_user_by_username(username)
    if not user or not verify_password_plain(password, user.get("password")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # remove password for safety
    u = user.copy()
    u.pop("password", None)
    logger.info(f"User {username} logged in")
    return u
    return u

# -----------------
# Compatibility endpoints (no tokens issued)
# -----------------
@app.post("/token")
def token(form_data: OAuth2PasswordRequestForm = Depends()):

    user = fetch_user_by_username(form_data.username)
    if not user or not verify_password_plain(form_data.password, user.get("password")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    u = user.copy(); u.pop("password", None)
    return {"access_granted": True, "user": u}

@app.post("/login")
def login(payload: LoginIn):

    user = fetch_user_by_username(payload.username)
    if not user or not verify_password_plain(payload.password, user.get("password")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    u = user.copy(); u.pop("password", None)
    return {"user": u}

# -----------------
# Admin convenience: create admin (DEV only)
# -----------------
@app.post("/register_admin")
def register_admin(username: str, password: str, name: str = "Admin", phone: str = None, email: str = None):

    existing = fetch_user_by_username(username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    admin_id = db_add_and_delete_entries.create_member_with_credentials(
        name=name,
        age=30,
        gender="other",
        joined_date=datetime.utcnow().date().isoformat(),
        phone=phone,
        email=email,
        username=username,
        hashed_password=password,
        role="admin",
    )
    logger.info(f"Admin created id={admin_id} username={username}")
    return {"admin_id": admin_id, "username": username}

# -----------------
# /me
# -----------------
@app.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    u = current_user.copy()
    u.pop("password", None)
    return u

# -----------------
# Members endpoints (enforced)
# -----------------
@app.post("/add_members")
def add_members(member: MemberInfoIn, current_user: dict = Depends(get_current_user)):
    # only admin allowed
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    mid = db_add_and_delete_entries.add_member(
        member.name,
        member.age,
        member.gender,
        member.joined_date.date().isoformat(),
        member.phone,
        member.email,
        member.username,
        member.password,
    )
    return {"id": mid}

@app.get("/all_members")
def all_members(current_user: dict = Depends(get_current_user)):

    if current_user.get("role") == "admin":
        return db_get_info.get_all_members()
    return [db_get_info.get_member_by_id(current_user.get("id"))]

@app.get("/info_by_id/{member_id}")
def info_by_id(member_id: int, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin" and current_user.get("id") != member_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return db_get_info.get_member_by_id(member_id)

@app.get("/info_by_name/{member_name}")
def info_by_name(member_name: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return db_get_info.get_members_by_name(member_name)

@app.get("/info_by_gender/{member_gender}")
def info_by_gender(member_gender: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return db_get_info.get_members_by_gender(member_gender)

@app.put("/members/{member_id}")
def update_member(member_id: int, member: MemberInfoIn, current_user: dict = Depends(get_current_user)):

    if current_user.get("role") != "admin" and current_user.get("id") != member_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    rows = db_add_and_delete_entries.update_member(
        member_id,
        name=member.name,
        age=member.age,
        gender=member.gender,
        joined_date=member.joined_date.date().isoformat(),
        phone=member.phone,
        email=member.email,
        username=member.username,
        password=member.password,
    )
    logger.info(f"Admin updated id={member_id} username={member.username}")
    return {"updated": rows}

@app.delete("/members/{member_id}")
def delete_member(member_id: int, current_user: dict = Depends(get_current_user)):

    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    rows = db_add_and_delete_entries.delete_member(member_id)
    return {"deleted_rows": rows}

# -----------------
# Exercises
# -----------------
@app.post("/exercises")
def add_exercise(name: str, muscle_group: Optional[str] = None, equipment: Optional[str] = None,
                 current_user: dict = Depends(get_current_user)):
    # admin only
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    eid = db_add_and_delete_entries.add_exercise(name, muscle_group, equipment)
    return {"id": eid}

@app.get("/exercises")
def list_exercises(current_user: dict = Depends(get_current_user)):
    # both members and admins can list exercises
    return db_get_info.get_all_exercises()

# -----------------
# Sessions / Logs / Measurements (enforced)
# -----------------
@app.post("/sessions")
def create_session(payload: SessionCreate, current_user: dict = Depends(get_current_user)):
    # admin can create for anyone; member only for themselves
    if current_user.get("role") != "admin" and payload.member_id != current_user.get("id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    sid = db_add_and_delete_entries.add_workout_session(
        payload.member_id,
        payload.session_date.date().isoformat(),
        payload.total_duration,
        payload.notes,
    )
    logger.info(f"User created session id={sid}")
    return {"id": sid}

@app.get("/sessions/member/{member_id}")
def sessions_for_member(member_id: int, start: Optional[str] = None, end: Optional[str] = None,
                        current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin" and member_id != current_user.get("id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return db_get_info.get_sessions_for_member(member_id, start, end)

@app.post("/logs")
def create_log(payload: LogCreate, current_user: dict = Depends(get_current_user)):
    session = db_get_info.get_session_by_id(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.get("role") != "admin" and session.get("member_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")
    lid = db_add_and_delete_entries.add_workout_log(
        payload.session_id, payload.exercise_id, payload.sets, payload.reps, payload.weight, payload.calories_burned
    )
    logger.info(f"User created log id={lid}")
    return {"id": lid}

@app.get("/logs/session/{session_id}")
def logs_for_session(session_id: int, current_user: dict = Depends(get_current_user)):
    session = db_get_info.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.get("role") != "admin" and session.get("member_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")
    return db_get_info.get_logs_for_session(session_id)

@app.post("/measurements")
def create_measurement(payload: MeasurementCreate, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin" and payload.member_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")
    mid = db_add_and_delete_entries.add_body_measurement(
        payload.member_id, payload.measure_date.date().isoformat(), payload.weight, payload.chest, payload.arms, payload.waist, payload.notes
    )
    logger.info(f"User created measurement id={mid}")
    return {"id": mid}

@app.get("/measurements/member/{member_id}")
def measurements_for_member(member_id: int, start: Optional[str] = None, end: Optional[str] = None,
                            current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin" and member_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")
    return db_get_info.get_measurements_for_member(member_id, start, end)

# -----------------
# Analytics endpoints (enforced)
# -----------------
@app.get("/analytics/weekly_volume")
def analytics_weekly_volume(member_id: int, weeks: int = Query(12, gt=0, le=52),
                            current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin" and member_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")

    rows = db_get_info.raw_query(
        """
        SELECT wl.sets, wl.reps, IFNULL(wl.weight,0) AS weight, ws.session_date
        FROM workout_logs wl
        JOIN workout_sessions ws ON wl.session_id = ws.id
        WHERE ws.member_id = %s AND ws.session_date >= DATE_SUB(CURDATE(), INTERVAL %s WEEK)
        """,
        (member_id, weeks),
    )
    if not rows:
        return {"weekly_volume": []}
    df = pd.DataFrame(rows)
    df["volume"] = df["sets"] * df["reps"] * df["weight"]
    df["week"] = pd.to_datetime(df["session_date"]).dt.to_period("W").astype(str)
    out = df.groupby("week")["volume"].sum().reset_index().to_dict(orient="records")
    logger.info("Weekly volume calculation")
    return {"weekly_volume": out}

@app.get("/analytics/top_exercises")
def top_exercises(member_id: int, limit: int = 10, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin" and member_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")
    rows = db_get_info.get_top_exercises_for_member(member_id, limit)
    return {"top_exercises": rows}

# -----------------
# Health / debug
# -----------------
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
