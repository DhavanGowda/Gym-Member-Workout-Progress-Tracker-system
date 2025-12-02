# app_analytics_ui.py
import streamlit as st
import pandas as pd
from datetime import datetime
import io

from app_ui import safe_request

# ------------------------
# Helper Functions
# ------------------------
def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def compute_avg_duration_per_week(sessions: pd.DataFrame) -> pd.DataFrame:
    if sessions.empty:
        return pd.DataFrame(columns=["week", "avg_duration_minutes"])
    df = sessions.copy()
    df["session_date"] = pd.to_datetime(df["session_date"])
    df["week"] = df["session_date"].dt.to_period("W").astype(str)
    grouped = df.groupby("week")["total_duration"].mean().reset_index()
    grouped = grouped.rename(columns={"total_duration": "avg_duration_minutes"})
    return grouped.sort_values("week")

def compute_body_changes_monthly(measures: pd.DataFrame) -> pd.DataFrame:
    if measures.empty:
        return pd.DataFrame(columns=["month", "weight", "chest", "arms", "waist"])
    df = measures.copy()
    df["measure_date"] = pd.to_datetime(df["measure_date"])
    df["month"] = df["measure_date"].dt.to_period("M").astype(str)
    agg = df.groupby("month").agg({
        "weight": "mean",
        "chest": "mean",
        "arms": "mean",
        "waist": "mean",
    }).reset_index()
    return agg.sort_values("month")

# ------------------------
# TAB 1 — Avg Duration
# ------------------------
def avg_duration_tab(member_id: int):
    st.subheader("Average Workout Duration per Week")

    resp, err = safe_request("get", f"/sessions/member/{member_id}", params={})
    if err:
        st.error(err); return

    sessions = pd.DataFrame(resp.json() or [])
    if sessions.empty or "total_duration" not in sessions.columns:
        st.info("Not enough session data.")
        return

    df_week = compute_avg_duration_per_week(sessions)
    st.dataframe(df_week)

    if not df_week.empty:
        chart_data = df_week.set_index("week")["avg_duration_minutes"]
        st.bar_chart(chart_data)

        st.download_button(
            "Download Table (CSV)",
            df_to_csv_bytes(df_week),
            "avg_duration.csv",
            "text/csv"
        )

# ------------------------
# TAB 2 — Weekly Volume
# ------------------------
def avg_volume_tab(member_id: int):
    st.subheader("Weekly Workout Volume")

    weeks = st.slider("Last N weeks", 4, 52, 12)

    resp, err = safe_request("get", "/analytics/weekly_volume",
                             params={"member_id": member_id, "weeks": weeks})
    if err:
        st.error(err); return

    df = pd.DataFrame(resp.json().get("weekly_volume", []))

    if df.empty:
        st.info("No workout logs found.")
        return

    st.dataframe(df)

    chart_data = df.set_index("week")["volume"]
    st.bar_chart(chart_data)

    st.download_button(
        "Download Table (CSV)",
        df_to_csv_bytes(df),
        "weekly_volume.csv",
        "text/csv"
    )

# ------------------------
# TAB 3 — Body Changes
# ------------------------
def body_changes_tab(member_id: int):
    st.subheader("Body Measurements Over Time (Monthly)")

    resp, err = safe_request("get", f"/measurements/member/{member_id}", params={})
    if err:
        st.error(err); return

    df = pd.DataFrame(resp.json() or [])

    if df.empty:
        st.info("No body measurements available.")
        return

    df["measure_date"] = pd.to_datetime(df["measure_date"])
    df = df.sort_values("measure_date")

    monthly = compute_body_changes_monthly(df)
    st.dataframe(monthly)

    if not monthly.empty:
        monthly_chart = monthly.set_index("month")[["weight", "chest", "arms", "waist"]]
        st.line_chart(monthly_chart)

        st.download_button(
            "Download Table (CSV)",
            df_to_csv_bytes(monthly),
            "body_changes.csv",
            "text/csv"
        )

# ------------------------
# Main Analytics UI
# ------------------------
def show_analytics_ui():
    st.title("Analytics Dashboard")

    user = st.session_state.get("auth_user")
    if not user:
        st.info("Login to view analytics.")
        return

    # Member sees only their data; admin can enter ID
    if user.get("role") == "admin":
        member_id = st.number_input("Member ID", min_value=1, value=user.get("id", 1))
    else:
        member_id = user.get("id")

    tab1, tab2, tab3 = st.tabs(["Avg Duration", "Weekly Volume", "Body Changes"])

    with tab1:
        avg_duration_tab(member_id)

    with tab2:
        avg_volume_tab(member_id)

    with tab3:
        body_changes_tab(member_id)
