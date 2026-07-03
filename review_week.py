"""
review_week.py — close out a week: confirm tasks, reflect on aims,
carry unmade meals forward.
"""
from datetime import date
import streamlit as st
import pandas as pd

from sheets import load_task_library, load_view_weeks, save_task_library, save_view_weeks
from logic import DAYS, parse_week_range, split_tasks_cell, join_tasks, format_date, day_dates


def render():
    st.title("🔍 Review Week")
    st.caption("Close the loop: what got done, how the aims went, what carries forward.")

    try:
        task_df = load_task_library()
        view_df = load_view_weeks()
    except Exception as e:
        st.error(f"Couldn't reach the Google Sheet. Check your connection settings in SETUP.md.\n\n{e}")
        return

    if view_df.empty:
        st.info("No weeks to review yet — plan one first in **Create Week**.")
        return

    labels = view_df["Dates of Week"].tolist()
    # default to the most recent week
    def sort_key(lbl):
        rng = parse_week_range(lbl)
        return rng[0] if rng else date.min
    ordered = sorted(labels, key=sort_key, reverse=True)

    selected = st.selectbox("Which week are you reviewing?", ordered)
    row_idx = view_df.index[view_df["Dates of Week"] == selected][0]
    row = view_df.loc[row_idx]

    rng = parse_week_range(selected)
    dates = day_dates(rng[0]) if rng else {}

    tab_tasks, tab_aims, tab_meals = st.tabs(
        ["✅ Tasks", "🎯 Aims Reflection", "🍽️ Meal Carryover"]
    )

    with tab_tasks:
        _tasks_phase(task_df, row, dates, selected)
    with tab_aims:
        _aims_phase(view_df, row_idx, row, selected)
    with tab_meals:
        _meals_phase(view_df, row_idx, row, selected)


# ── Phase 1: Task confirmation ───────────────────────────────────────────
def _tasks_phase(task_df, row, dates, week_label):
    pairs = []
    for d in DAYS:
        for t in split_tasks_cell(row.get(f"{d} Tasks", "")):
            pairs.append((d, t))

    if not pairs:
        st.caption("No tasks were scheduled this week.")
        return

    st.caption("Check off what got done, and confirm the date it happened.")
    responses = {}
    for d, t in pairs:
        match = task_df[task_df["Task Name"] == t]
        current_status = match["Task Status"].iloc[0] if not match.empty else "Incomplete"
        current_comp = match["Completion Date (If Applicable)"].iloc[0] if not match.empty else ""

        c1, c2, c3 = st.columns([3, 1, 2])
        with c1:
            st.markdown(f"**{t}**")
            st.caption(f"Planned for {d}")
        with c2:
            done = st.checkbox(
                "Done", value=(current_status.strip().lower() == "complete"),
                key=f"rw_done_{week_label}_{d}_{t}",
            )
        with c3:
            default_date = dates.get(d, date.today())
            comp_date = None
            if done:
                comp_date = st.date_input(
                    "Completed on", value=default_date,
                    key=f"rw_date_{week_label}_{d}_{t}", label_visibility="collapsed",
                )
        responses[(d, t)] = (done, comp_date)

    if st.button("💾 Save Task Progress"):
        updated = task_df.copy()
        for (d, t), (done, comp_date) in responses.items():
            mask = updated["Task Name"] == t
            if mask.any():
                idx = updated[mask].index[0]
                if done:
                    updated.loc[idx, "Task Status"] = "Complete"
                    updated.loc[idx, "Completion Date (If Applicable)"] = format_date(comp_date)
                else:
                    updated.loc[idx, "Task Status"] = "Incomplete"
        save_task_library(updated)
        st.success("Task progress saved.")


# ── Phase 2: Aims reflection ─────────────────────────────────────────────
def _aims_phase(view_df, row_idx, row, week_label):
    for who in ["Isaac", "Madison", "Family"]:
        st.markdown(f"**{who}'s Aim:** {row.get(f'{who} Aim', '') or '_none set_'}")
        st.session_state[f"rw_refl_{week_label}_{who}"] = st.text_area(
            f"How did it go for {who}?",
            value=row.get(f"{who} Reflection", ""),
            key=f"rw_refl_input_{week_label}_{who}",
            height=90,
        )
        st.markdown("---")

    if st.button("💾 Save Reflections"):
        updated = view_df.copy()
        for who in ["Isaac", "Madison", "Family"]:
            updated.loc[row_idx, f"{who} Reflection"] = st.session_state[f"rw_refl_{week_label}_{who}"]
        save_view_weeks(updated)
        st.success("Reflections saved.")


# ── Phase 3: Meal carryover ───────────────────────────────────────────────
def _meals_phase(view_df, row_idx, row, week_label):
    st.caption("Bought the ingredients but never made it? Carry it into next week's shuffle.")
    already_carried = set(split_tasks_cell(row.get("Carryover Meals", "")))
    selections = {}
    for d in DAYS:
        meal = row.get(f"{d} Dinner", "")
        if not meal:
            continue
        selections[meal] = st.checkbox(
            f"{d}: {meal} — carry to next week",
            value=(meal in already_carried),
            key=f"rw_carry_{week_label}_{d}",
        )

    if st.button("💾 Save Carryover"):
        carry_list = [m for m, checked in selections.items() if checked]
        updated = view_df.copy()
        updated.loc[row_idx, "Carryover Meals"] = join_tasks(carry_list)
        save_view_weeks(updated)
        st.success("Carryover saved — it'll be offered at the top of next week's Meals tab.")
