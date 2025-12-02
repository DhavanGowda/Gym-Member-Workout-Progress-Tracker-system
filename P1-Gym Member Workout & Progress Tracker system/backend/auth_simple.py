# auth_basic.py
"""
Simple HTTP Basic auth for local/dev use.
Checks username/password against members.username / members.password (plain-text).
Provides:
 - get_current_user: FastAPI dependency returning user dict
 - require_admin: FastAPI dependency requiring admin role
 - login_endpoint_compatible: helper function to use for a /login route (optional)
No tokens, no jose, no external packages besides FastAPI's built-in HTTPBasic.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import db_get_info
import db_add_and_delete_entries
import secrets

security = HTTPBasic()

def verify_password_plain(plain: str, stored: str) -> bool:
    """Plain-text comparison. DEV only."""
    if stored is None:
        return False
    # Use secrets.compare_digest to avoid timing attacks (minor)
    return secrets.compare_digest(str(plain), str(stored))

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """
    FastAPI dependency. Use in routes:
      current_user: dict = Depends(auth.get_current_user)
    It returns the user row dict on success or raises 401.
    """
    username = credentials.username
    password = credentials.password
    user = db_get_info.get_member_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    stored = user.get("password")
    if not verify_password_plain(password, stored):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # remove password before returning (safety)
    u = user.copy()
    u.pop("password", None)
    return u

def require_admin(current_user: dict = Depends(get_current_user)):

    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user

def login_endpoint_compatible(credentials: HTTPBasicCredentials = Depends(security)):
    return get_current_user(credentials)
