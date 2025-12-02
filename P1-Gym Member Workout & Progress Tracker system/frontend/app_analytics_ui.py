import streamlit as st
import pandas as pd
from datetime import datetime
import io

# safe_request is expected to be in app_ui.py (same project)
from app_ui import safe_request

# ------------------------
# Helpers
# ------------------------
def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def normalize_json_to_df(obj) -> pd.DataFrame:
    """
    Convert various API JSON shapes into a pandas DataFrame safely:
      - If obj is list -> DataFrame(list)
      - If obj is dict and contains a list under common keys -> DataFrame(that list)
      - If obj is dict with scalar fields -> DataFrame([obj])  (single-row)
      - If obj is None or empty -> empty DataFrame()
    This avoids `ValueError: If using all scalar values...` when API returns a dict.
    """
    if obj is None:
        return pd.DataFrame()

    # If already a DataFrame-compatible list
    if isinstance(obj, list):
        return pd.DataFrame(obj)

    # If dict, try to find an inner list
    if isinstance(obj, dict):
        # Common possible keys that contain lists
        list_keys = ['sessions', 'data', 'results', 'weekly_volume', 'measurements', 'members', 'logs']
        for k in list_keys:
            if k in obj and isinstance(obj[k], list):
                return pd.DataFrame(obj[k])

        # If dict values themselves are lists and all have same length -> build DF from dict
        list_values = [v for v in obj.values() if isinstance(v, list)]
        if list_values and all(isinstance(v, list) for v in list_values):
            try:
                return pd.DataFrame(obj)
            except Exception:
                pass

        # Otherwise treat dict as a single row
        return pd.DataFrame([obj])

    # Fallback: wrap into DataFrame
    try:
        return pd.DataFrame(obj)
    except Exception:
        return pd.DataFrame()

# ------------------------
# Analytics computations
# ------------------------
def compute_avg_duration_per_week(sessions: pd.DataFrame) -> pd.DataFrame:
    if sessions.empty:
        return pd.DataFrame(columns=["week", "avg_duration_minutes"])
    df = sessions.copy()
    # ensure session_date and total_duration exist
    if "session_date" not in df.columns or "total_duration" not in df.columns:
        return pd.DataFrame(columns=["week", "avg_duration_minutes"])
    df["session_date"] = pd.to_datetime(df["session_date"])
    df["week"] = df["session_date"].dt.to_period("W").astype(str)
    grouped = df.groupby("week")["total_duration"].mean().reset_index()
    grouped = grouped.rename(columns={"total_duration": "avg_duration_minutes"})
    return grouped.sort_values("week")

def compute_body_changes_monthly(measures: pd.DataFrame) -> pd.DataFrame:
    if measures.empty:
        return pd.DataFrame(columns=["month", "weight", "chest", "arms", "waist"])
    df = measures.copy()
    if "measure_date" not in df.columns:
        return pd.DataFrame(columns=["month", "weight", "chest", "arms", "waist"])
    df["measure_date"] = pd.to_datetime(df["measure_date"])
    df["month"] = df["measure_date"].dt.to_period("M").astype(str)
    # pick relevant columns if present
    agg_cols = {}
    for col in ("weight", "chest", "arms", "waist"):
        if col in df.columns:
            agg_cols[col] = "mean"
    if not agg_cols:
        return pd.DataFrame(columns=["month"])
    agg = df.groupby("month").agg(agg_cols).reset_index()
    return agg.sort_values("month")

# ------------------------
# TAB: Avg Duration
# ------------------------
def avg_duration_tab(member_id: int):
    st.subheader("Average Workout Duration per Week")
    resp, err = safe_request("get", f"/sessions/member/{member_id}", params={})
    if err:
        st.error(err); return
    if resp.status_code != 200:
        st.error(f"Failed to fetch sessions: {resp.status_code} {resp.text}"); return

    raw = resp.json()
    sessions = normalize_json_to_df(raw)

    if sessions.empty:
        st.info("No session records found.")
        return

    df_week = compute_avg_duration_per_week(sessions)
    if df_week.empty:
        st.info("Not enough data to compute weekly averages.")
        return

    st.dataframe(df_week)
    chart_data = df_week.set_index("week")["avg_duration_minutes"]
    st.bar_chart(chart_data)

    st.download_button("Download table (CSV)", df_to_csv_bytes(df_week), "avg_duration_per_week.csv", "text/csv")

# ------------------------
# TAB: Weekly Volume
# ------------------------
def avg_volume_tab(member_id: int):
    st.subheader("Weekly Workout Volume")
    weeks = st.slider("Number of recent weeks to fetch", 4, 52, 12)
    resp, err = safe_request("get", "/analytics/weekly_volume", params={"member_id": member_id, "weeks": weeks})
    if err:
        st.error(err); return
    if resp.status_code != 200:
        st.error(f"API error: {resp.status_code} {resp.text}"); return

    raw = resp.json()
    # API expected to return {"weekly_volume":[{week:..., volume:...}, ...]}
    # normalize_json_to_df will handle both dict and lists
    df_vol = None
    if isinstance(raw, dict) and "weekly_volume" in raw:
        df_vol = normalize_json_to_df(raw["weekly_volume"])
    else:
        df_vol = normalize_json_to_df(raw)

    if df_vol.empty:
        st.info("No volume data available.")
        return

    # ensure expected column names
    if "week" not in df_vol.columns or "volume" not in df_vol.columns:
        st.warning("Volume data missing expected columns ('week','volume'). Showing raw table.")
        st.dataframe(df_vol)
        return

    st.dataframe(df_vol)
    chart_data = df_vol.set_index("week")["volume"]
    st.bar_chart(chart_data)

    st.metric("Average weekly volume", f"{df_vol['volume'].mean():.1f}")
    st.download_button("Download table (CSV)", df_to_csv_bytes(df_vol), "weekly_volume.csv", "text/csv")

# ------------------------
# TAB: Body Changes
# ------------------------
def body_changes_tab(member_id: int):
    st.subheader("Body Measurements Over Months")
    resp, err = safe_request("get", f"/measurements/member/{member_id}", params={})
    if err:
        st.error(err); return
    if resp.status_code != 200:
        st.error(f"Failed to fetch measurements: {resp.status_code} {resp.text}"); return

    raw = resp.json()
    measures = normalize_json_to_df(raw)
    if measures.empty:
        st.info("No body measurements found for this member.")
        return

    # keep relevant columns
    measures["measure_date"] = pd.to_datetime(measures["measure_date"])
    measures = measures.sort_values("measure_date")
    monthly = compute_body_changes_monthly(measures)
    if monthly.empty:
        st.info("Not enough measurement data to plot monthly trends.")
        return

    st.dataframe(monthly)
    # set index to month and show multiple series on line chart
    chart_df = monthly.set_index("month")
    st.line_chart(chart_df)

    st.download_button("Download table (CSV)", df_to_csv_bytes(monthly), "body_changes_monthly.csv", "text/csv")

# ------------------------
# Main analytics UI
# ------------------------
def show_analytics_ui():
    st.title("Gym Tracker — Analytics Dashboard")
    user = st.session_state.get("auth_user")
    if not user:
        st.info("Login to view analytics.")
        return

    if user.get("role") == "admin":
        member_id = st.number_input("Member ID (select)", min_value=1, value=user.get("id", 1))
    else:
        member_id = user.get("id")

    tab1, tab2, tab3 = st.tabs(["Avg Duration", "Weekly Volume", "Body Changes"])
    with tab1:
        avg_duration_tab(member_id)
    with tab2:
        avg_volume_tab(member_id)
    with tab3:
        body_changes_tab(member_id)

if __name__ == "__main__":
    show_analytics_ui()