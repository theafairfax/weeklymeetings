"""
sheets.py — Google Sheets connection + read/write helpers for the
Weekly Meetings app.

Backed by st.connection("gsheets", type=GSheetsConnection) from the
st-gsheets-connection package (imported as streamlit_gsheets). See
SETUP.md for how to point this at your spreadsheet.
"""
import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ── Worksheet (tab) names — must match your Google Sheet's tab names ────────
MEAL_WS = "Meal Library"
TASK_WS = "Task Library"
VIEW_WS = "View Weeks"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MEAL_COLS = ["Protein", "Side", "Course"]

TASK_COLS = [
    "Task Name",
    "Task Description",
    "Task Type",
    "Date (If Applicable)",
    "Due Date (If Applicable)",
    "Task Status",
    "Completion Date (If Applicable)",
]

# View Weeks keeps the original columns from your sheet, plus three
# reflection columns and a carryover-meals column used by Review Week.
# If your sheet doesn't have these last four columns yet, they'll be
# created automatically the first time a week is saved through the app.
VIEW_COLS = (
    ["Dates of Week"]
    + [f"{d} Dinner" for d in DAYS]
    + ["Isaac Aim", "Madison Aim", "Family Aim"]
    + [f"{d} Tasks" for d in DAYS]
    + ["Isaac Reflection", "Madison Reflection", "Family Reflection", "Carryover Meals"]
)


def _conn():
    return st.connection("gsheets", type=GSheetsConnection)


def _clean(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    if df is None:
        df = pd.DataFrame(columns=cols)
    df = df.dropna(how="all").copy()
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    return df.fillna("").astype(str)


def load_meal_library() -> pd.DataFrame:
    df = _conn().read(worksheet=MEAL_WS, ttl=0)
    return _clean(df, MEAL_COLS)


def load_task_library() -> pd.DataFrame:
    df = _conn().read(worksheet=TASK_WS, ttl=0)
    return _clean(df, TASK_COLS)


def load_view_weeks() -> pd.DataFrame:
    df = _conn().read(worksheet=VIEW_WS, ttl=0)
    return _clean(df, VIEW_COLS)


def save_meal_library(df: pd.DataFrame) -> None:
    _conn().update(worksheet=MEAL_WS, data=df[MEAL_COLS])


def save_task_library(df: pd.DataFrame) -> None:
    _conn().update(worksheet=TASK_WS, data=df[TASK_COLS])


def save_view_weeks(df: pd.DataFrame) -> None:
    _conn().update(worksheet=VIEW_WS, data=df[VIEW_COLS])
