# app_ui.py
# app_ui.py (tokenless, sends username/password on every protected request)
import streamlit as st
import requests
import pandas as pd
from datetime import date
from typing import Optional, Dict, Any

# ---------- config ----------
DEFAULT_API = "http://localhost:8000"
REQUEST_TIMEOUT = 6  # seconds

# ---------- helpers ----------
def ensure_api():
    if "API" not in st.session_state:
        st.session_state["API"] = DEFAULT_API
    return st.session_state["API"].rstrip("/")

# Credentials helpers: store credentials separately (username/password)
def set_credentials(username: str, password: str):
    st.session_state['credentials'] = {"username": username, "password": password}

def clear_credentials():
    st.session_state['credentials'] = None

def get_credentials() -> Optional[Dict[str, str]]:
    return st.session_state.get('credentials')

# Build auth headers used by safe_request
def auth_headers() -> Dict[str, str]:
    creds = get_credentials()
    if not creds:
        return {}
    return {"X-Username": creds["username"], "X-Password": creds["password"], "Content-Type": "application/json"}

def inject_auth_into_json(json_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = {} if json_payload is None else dict(json_payload)
    creds = get_credentials()
    if creds:
        payload.setdefault("auth", {})
        payload["auth"].setdefault("username", creds["username"])
        payload["auth"].setdefault("password", creds["password"])
    return payload

def safe_request(method: str, path: str, *, json: Optional[Dict[str, Any]] = None,
                 data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None, timeout: int = REQUEST_TIMEOUT):
    """
    Wrapper for requests that injects auth headers and auth JSON block for POST/PUT/PATCH.
    Returns (response, None) or (None, error_message).
    """
    base = ensure_api()
    if not path.startswith("/"):
        path = "/" + path
    url = base + path

    hdrs = {}
    if headers:
        hdrs.update(headers)
    hdrs.update(auth_headers())

    if method.lower() in ("post", "put", "patch"):
        json = inject_auth_into_json(json)

    try:
        func = getattr(requests, method.lower())
        resp = func(url, json=json, data=data, params=params, headers=hdrs, timeout=timeout)
        return resp, None
    except requests.exceptions.ConnectionError:
        return None, f"Cannot connect to backend at {base}. Is the server running?"
    except requests.exceptions.Timeout:
        return None, "Request timed out. Try again."
    except Exception as e:
        return None, f"Unexpected error: {e}"

# ---------- auth / login UI ----------
def login_widget():
    """
    Tokenless login: calls POST /login and on success stores:
      - st.session_state['auth_user'] = user dict (from server)
      - st.session_state['credentials'] = {'username': username, 'password': password}
    """
    st.sidebar.header('Login')
    # Ensure keys exist
    if 'auth_user' not in st.session_state:
        st.session_state['auth_user'] = None
    if 'credentials' not in st.session_state:
        st.session_state['credentials'] = None

    if not st.session_state.get('auth_user'):
        username = st.sidebar.text_input('Username', key="ui_login_username")
        password = st.sidebar.text_input('Password', type='password', key="ui_login_password")
        if st.sidebar.button('Login'):
            if not username or not password:
                st.sidebar.error("Enter username and password.")
                return
            # call backend /login (expects JSON {username, password})
            resp, err = safe_request("post", "/login", json={"username": username, "password": password})
            if err:
                st.sidebar.error(err)
                return
            if resp.status_code == 200:
                body = resp.json()
                user = body.get("user") or body
                # store user info (no password)
                st.session_state['auth_user'] = user
                # store credentials separately for future requests (minimal change)
                set_credentials(username, password)
                st.sidebar.success(f"Logged in: {user.get('username', '<unknown>')}")
            else:
                # show server message if present
                try:
                    detail = resp.json().get("detail")
                    st.sidebar.error(f"Login failed: {detail}")
                except Exception:
                    st.sidebar.error(f"Login failed: {resp.status_code} {resp.text}")
    else:
        user = st.session_state.get('auth_user') or {}
        st.sidebar.write(f"User: **{user.get('username','-')}**")
        st.sidebar.write(f"Role: **{user.get('role','-')}**")
        if st.sidebar.button('Logout'):
            st.session_state['auth_user'] = None
            clear_credentials()
            st.sidebar.success('Logged out')

# ---------- admin: add member ----------
def add_member_form():
    st.header('Add Member (Admin only)')
    with st.form('add_member_form'):
        name = st.text_input('Name')
        age = st.number_input('Age', min_value=0, value=20)
        gender = st.selectbox('Gender', ['male', 'female', 'other'])
        joined_date = st.date_input('Joined date', value=date.today())
        phone = st.text_input('Phone')
        email = st.text_input('Email')
        username = st.text_input('Username for new member')
        password = st.text_input('Password for new member')
        submitted = st.form_submit_button('Add Member')
        if submitted:
            payload = {
                'name': name, 'age': int(age), 'gender': gender,
                'joined_date': joined_date.isoformat(), 'phone': phone, 'email': email,
                'username': username, 'password': password
            }
            resp, err = safe_request("post", "/add_members", json=payload)
            if err:
                st.error(err); return
            if resp.status_code in (200, 201):
                st.success('Member added')
            elif resp.status_code == 401:
                st.error("Unauthorized. Check credentials.")
            else:
                st.error(f"Error: {resp.status_code} {resp.text}")

# ---------- view members ----------
def view_members():
    st.header('Members')

    # require login
    if not st.session_state.get('auth_user'):
        st.info('Login to view members.')
        return

    user = st.session_state.get('auth_user')
    # admin: show all members
    if user.get('role') == 'admin':
        resp, err = safe_request("get", "/all_members")
        if err:
            st.error(err); return
        if resp.status_code == 200:
            members = resp.json() or []
            if not members:
                st.info('No members found.')
                return
            df = pd.DataFrame(members)
            if 'password' in df.columns:
                df = df.drop(columns=['password'])
            st.dataframe(df)
        elif resp.status_code == 401:
            st.error("Unauthorized. Please login as admin.")
        else:
            st.error(f'Failed to fetch members: {resp.status_code} {resp.text}')
    else:
        # member: show only their own info (use /me or /info_by_id)
        # try /me first if backend supports it
        resp, err = safe_request("get", "/me")
        if err:
            st.error(err); return
        if resp.status_code == 200:
            me = resp.json()
            # if /me returned a dict with user info
            if isinstance(me, dict) and me.get("id"):
                df = pd.DataFrame([me])
                if 'password' in df.columns:
                    df = df.drop(columns=['password'])
                st.dataframe(df)
                return
        # fallback: call info_by_id
        member_id = user.get("id")
        resp2, err2 = safe_request("get", f"/info_by_id/{member_id}")
        if err2:
            st.error(err2); return
        if resp2.status_code == 200:
            mem = resp2.json()
            # db_get_info.get_member_by_id may return dict or list; normalize
            if isinstance(mem, list):
                df = pd.DataFrame(mem)
            else:
                df = pd.DataFrame([mem])
            if 'password' in df.columns:
                df = df.drop(columns=['password'])
            st.dataframe(df)
        else:
            st.error(f"Failed to fetch your info: {resp2.status_code} {resp2.text}")

# ---------- admin: update member ----------
def update_member_form():
    st.header("Update Member (Admin only)")
    user = st.session_state.get('auth_user')
    if not user or user.get('role') != 'admin':
        st.info("Admin login required to update members.")
        return

    # allow admin to pick member id to edit
    member_id = st.number_input("Member ID to edit", min_value=1, value=1)
    if st.button("Load member data"):
        resp, err = safe_request("get", f"/info_by_id/{int(member_id)}")
        if err:
            st.error(err); return
        if resp.status_code == 200:
            mem = resp.json()
            # mem may be list or dict
            if isinstance(mem, list):
                mem = mem[0] if mem else {}
            st.session_state['_edit_member'] = mem
        else:
            st.error(f"Failed to load member: {resp.status_code} {resp.text}")
            return

    mem = st.session_state.get('_edit_member') or {}
    # show form prefilled if mem exists
    with st.form("update_member_form"):
        name = st.text_input("Name", value=mem.get('name', ''), key="edit_name")
        age = st.number_input("Age", min_value=0, value=int(mem.get('age', 20)), key="edit_age")
        gender = st.selectbox("Gender", ['male','female','other'], index=0 if mem.get('gender','male')=='male' else (1 if mem.get('gender','female')=='female' else 2), key="edit_gender")
        joined_date = st.date_input("Joined date", value=(pd.to_datetime(mem.get('joined_date')).date() if mem.get('joined_date') else date.today()), key="edit_joined")
        phone = st.text_input("Phone", value=mem.get('phone',''), key="edit_phone")
        email = st.text_input("Email", value=mem.get('email',''), key="edit_email")
        username=st.text_input("Username", value=mem.get('username',''), key="edit_username")
        password = st.text_input("Password", value=mem.get('password',''), key="edit_password")
        submitted = st.form_submit_button("Update Member")
        if submitted:
            payload = {
                "name": name,
                "age": int(age),
                "gender": gender,
                "joined_date": joined_date.isoformat(),
                "phone": phone,
                "email": email,
                "username": username,
                "password": password,
            }
            resp, err = safe_request("put", f"/members/{int(member_id)}", json=payload)
            if err:
                st.error(err); return
            if resp.status_code in (200,201):
                st.success("Member updated successfully.")
                # clear cached edit
                st.session_state.pop('_edit_member', None)
            else:
                st.error(f"Failed to update: {resp.status_code} {resp.text}")

# ---------- exercises ----------
def exercises_widget():
    st.header('Exercises')

    resp, err = safe_request("get", "/exercises")
    if err:
        st.error(err); return
    if resp.status_code == 200:
        ex = resp.json() or []
        if ex:
            st.table(pd.DataFrame(ex))
        else:
            st.info('No exercises found.')
    elif resp.status_code == 401:
        st.text("Unauthorized. Please login to view exercises.")
    else:
        st.error(f'Failed to fetch exercises: {resp.status_code} {resp.text}')

# ---------- sessions ----------
def add_session_form():
    st.header('Add Session')

    with st.form('session_form'):
        # if admin wants to create for any member, allow selection; otherwise default to own id
        user = st.session_state.get('auth_user') or {}
        default_member = user.get('id', 1)
        member_id = st.number_input('Member ID', min_value=1, value=default_member)
        session_date = st.date_input('Session date', value=date.today())
        duration = st.number_input('Duration (minutes)', min_value=0, value=45)
        notes = st.text_area('Notes')
        submit = st.form_submit_button('Create Session')

        if submit:
            payload = {
                'member_id': int(member_id),
                'session_date': session_date.isoformat(),
                'total_duration': int(duration),
                'notes': notes
            }

            resp, err = safe_request("post", "/sessions", json=payload)
            if err:
                st.error(err); return

            if resp.status_code in (200, 201):
                result = resp.json()
                session_id = result.get("id")
                if session_id is not None:
                    st.success(f"Session created successfully! Session ID = {session_id}")
                else:
                    st.success("Session created successfully, but server did not return an ID.")
            elif resp.status_code == 401:
                st.error(f"Unauthorized (401): {resp.json().get('detail', resp.text)}. Please login again.")
            else:
                st.error(f"Error: {resp.status_code} {resp.text}")

# ---------- logs ----------
def add_log_form():
    st.header('Add Workout Log')
    with st.form('log_form'):
        session_id = st.number_input('Session ID', min_value=1, value=1)
        exercise_id = st.number_input('Exercise ID', min_value=1, value=1)
        sets = st.number_input('Sets', min_value=1, value=3)
        reps = st.number_input('Reps', min_value=1, value=8)
        weight = st.number_input('Weight (kg)', min_value=0.0, value=20.0)
        calories = st.number_input('Calories burned', min_value=0.0, value=50.0)
        submit = st.form_submit_button('Add Log')
        if submit:
            payload = {'session_id': int(session_id), 'exercise_id': int(exercise_id),
                       'sets': int(sets), 'reps': int(reps), 'weight': float(weight),
                       'calories_burned': float(calories)}
            resp, err = safe_request("post", "/logs", json=payload)
            if err:
                st.error(err); return
            if resp.status_code in (200, 201):
                st.success('Log added')
            else:
                st.error(f'Error: {resp.status_code} {resp.text}')

# ---------- measurements ----------
def add_measurement_form():
    st.header('Add Body Measurement')
    with st.form('measure_form'):
        user = st.session_state.get('auth_user') or {}
        default_member = user.get('id', 1)
        member_id = st.number_input('Member ID', min_value=1, value=default_member)
        measure_date = st.date_input('Measure date', value=date.today())
        weight = st.number_input('Weight (kg)', min_value=0.0, value=70.0)
        chest = st.number_input('Chest (cm)', min_value=0.0, value=90.0)
        arms = st.number_input('Arms (cm)', min_value=0.0, value=30.0)
        waist = st.number_input('Waist (cm)', min_value=0.0, value=80.0)
        notes = st.text_area('Notes')
        submit = st.form_submit_button('Add Measurement')
        if submit:
            payload = {'member_id': int(member_id), 'measure_date': measure_date.isoformat(),
                       'weight': float(weight), 'chest': float(chest), 'arms': float(arms),
                       'waist': float(waist), 'notes': notes}
            resp, err = safe_request("post", "/measurements", json=payload)
            if err:
                st.error(err); return
            if resp.status_code in (200, 201):
                st.success('Measurement added')
            else:
                st.error(f'Error: {resp.status_code} {resp.text}')

# ---------- main UI assembly ----------
def show_app_ui():
    ensure_api()
    login_widget()

    col1, col2 = st.columns([2, 1])
    with col1:
        view_members()
        st.markdown('---')
        exercises_widget()
        st.markdown('---')
        # Admin update member section below members
        user = st.session_state.get('auth_user') or {}
        if user and user.get('role') == 'admin':
            update_member_form()
    with col2:
        user = st.session_state.get('auth_user')
        if user and user.get('role') == 'admin':
            add_member_form()
        else:
            st.info('Only admins can add members (login as admin).')
        st.markdown('---')
        add_session_form()
        st.markdown('---')
        add_log_form()
        st.markdown('---')
        add_measurement_form()

# Run UI when module executed directly
if __name__ == "__main__":
    show_app_ui()
