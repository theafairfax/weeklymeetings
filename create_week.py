"""
create_week.py — set the week's boundaries, then plan meals, tasks, aims, and save.
"""
import random
from datetime import timedelta

import streamlit as st
import pandas as pd

from sheets import (
    load_meal_library, load_task_library, load_view_weeks,
    save_meal_library, save_task_library, save_view_weeks,
)
from logic import (
    build_meal_pool, available_tasks, next_monday_after, format_date,
    join_tasks, split_tasks_cell,
)


def _init_state():
    defaults = {
        "cw_start_date": None,
        "cw_num_days": 7,
        "cw_active_days": [],          # list of (day_name, date) tuples
        "cw_boundaries_set": False,
        "cw_meals": {},
        "cw_carry_used": False,
        "cw_meals_approved": False,
        "cw_selected_tasks": [],
        "cw_tasks_by_day": {},
        "cw_tasks_approved": False,
        "cw_isaac_aim": "",
        "cw_madison_aim": "",
        "cw_family_aim": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset_wizard():
    for k in ["cw_start_date", "cw_num_days", "cw_active_days", "cw_boundaries_set",
              "cw_meals", "cw_carry_used", "cw_meals_approved", "cw_selected_tasks",
              "cw_tasks_by_day", "cw_tasks_approved", "cw_isaac_aim",
              "cw_madison_aim", "cw_family_aim"]:
        if k in st.session_state:
            del st.session_state[k]
    _init_state()


def _compute_active_days(start, num_days):
    """Build an ordered list of (day_name, date) tuples starting at `start`."""
    return [
        ((start + timedelta(days=i)).strftime("%A"), start + timedelta(days=i))
        for i in range(num_days)
    ]


# ── Local shuffle helpers ───────────────────────────────────────────────
# These live here (instead of relying on logic.py's shuffle_meals/shuffle_tasks)
# because those assume a fixed Monday–Sunday week. These work with whatever
# subset of days was set in the Boundaries phase.

def _shuffle_meals_for_days(pool, day_names, carryover=None, existing=None):
    carryover = carryover or []
    existing = existing or {}
    result = {}
    remaining_days = list(day_names)

    for meal in carryover:
        if not remaining_days:
            break
        result[remaining_days.pop(0)] = meal

    if not pool:
        for d in remaining_days:
            result[d] = existing.get(d, "")
        return result

    for d in remaining_days:
        if existing.get(d):
            result[d] = existing[d]
        else:
            result[d] = random.choice(pool)

    return result


def _shuffle_tasks_for_days(selected_tasks, day_names, existing=None):
    existing = existing or {}
    result = {d: [] for d in day_names}
    assigned = set()

    for d in day_names:
        for t in existing.get(d, []):
            if t in selected_tasks and t not in assigned:
                result[d].append(t)
                assigned.add(t)

    remaining = [t for t in selected_tasks if t not in assigned]
    random.shuffle(remaining)
    for t in remaining:
        result[random.choice(day_names)].append(t)

    return result


def render():
    st.title("🛠️ Create Week")
    st.caption("Set the week's boundaries, then plan meals, tasks, and aims.")

    try:
        meal_df = load_meal_library()
        task_df = load_task_library()
        view_df = load_view_weeks()
    except Exception as e:
        st.error(f"Couldn't reach the Google Sheet. Check your connection settings in SETUP.md.\n\n{e}")
        return

    _init_state()

    tab_bounds, tab_meals, tab_tasks, tab_aims, tab_save = st.tabs(
        ["📅 Boundaries", "🍽️ Meals", "✅ Tasks", "🎯 Aims", "💾 Save Week"]
    )

    with tab_bounds:
        _boundaries_phase(view_df)
    with tab_meals:
        _meals_phase(meal_df, view_df)
    with tab_tasks:
        _tasks_phase(task_df)
    with tab_aims:
        _aims_phase()
    with tab_save:
        _save_phase(task_df, view_df)


# ── Phase 0: Boundaries ─────────────────────────────────────────────────
def _boundaries_phase(view_df):
    st.subheader("📅 Set the boundaries for this week")
    st.caption(
        "Choose a start date and how many days you're planning. It doesn't have "
        "to start on Monday, and it doesn't have to be a full 7 days — plan a "
        "5-day stretch before a trip, or a full week starting Thursday, whatever fits."
    )

    suggested_start = next_monday_after(view_df)
    default_start = st.session_state.cw_start_date or suggested_start

    start = st.date_input("This week starts on", value=default_start, key="cw_bounds_start")
    num_days = st.slider(
        "How many days are you planning?", min_value=1, max_value=7,
        value=st.session_state.cw_num_days, key="cw_bounds_numdays",
    )

    preview_days = _compute_active_days(start, num_days)

    st.markdown("**Days included:**")
    cols = st.columns(len(preview_days))
    for col, (name, d) in zip(cols, preview_days):
        with col:
            st.markdown(f"**{name}**")
            st.caption(format_date(d))

    st.markdown("---")
    if st.button("✅ Set These Boundaries"):
        st.session_state.cw_start_date = start
        st.session_state.cw_num_days = num_days
        st.session_state.cw_active_days = preview_days
        st.session_state.cw_boundaries_set = True
        st.success(
            f"Boundaries set: {preview_days[0][0]} {format_date(preview_days[0][1])} → "
            f"{preview_days[-1][0]} {format_date(preview_days[-1][1])}. Move on to Meals →"
        )

    if st.session_state.cw_boundaries_set:
        active = st.session_state.cw_active_days
        st.info(
            f"Current plan: {len(active)} day(s), starting "
            f"{active[0][0]} {format_date(active[0][1])}."
        )


# ── Phase 1: Meals ──────────────────────────────────────────────────────
def _meals_phase(meal_df, view_df):
    if not st.session_state.cw_boundaries_set:
        st.warning("Set your week's boundaries first (📅 Boundaries tab).")
        return

    day_names = [name for name, _ in st.session_state.cw_active_days]

    pool = build_meal_pool(meal_df)
    if not pool:
        st.warning("Your Meal Library is empty — add a Protein/Side/Course below first.")

    # look for carryover meals from the most recent past week
    carry_list = []
    if not view_df.empty:
        latest_row = view_df.iloc[-1]
        carry_list = split_tasks_cell(latest_row.get("Carryover Meals", ""))

    if carry_list and not st.session_state.cw_carry_used:
        st.info(f"🍽️ Carried over from last week: **{', '.join(carry_list)}**")
        if st.button("↩️ Pull carryover meals into this week"):
            for i, d in enumerate(day_names):
                if i < len(carry_list) and f"cw_meal_sel_{d}" in st.session_state:
                    del st.session_state[f"cw_meal_sel_{d}"]

            st.session_state.cw_meals = _shuffle_meals_for_days(
                pool, day_names, carryover=carry_list, existing=st.session_state.cw_meals
            )
            st.session_state.cw_carry_used = True
            st.rerun()

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("🎲 Shuffle All Meals"):
            for d in day_names:
                if f"cw_meal_sel_{d}" in st.session_state:
                    del st.session_state[f"cw_meal_sel_{d}"]
            st.session_state.cw_meals = _shuffle_meals_for_days(pool, day_names)
            st.rerun()

    with col_b:
        if st.button("🎲 Shuffle Remaining Days"):
            for d in day_names:
                if not st.session_state.cw_meals.get(d) and f"cw_meal_sel_{d}" in st.session_state:
                    del st.session_state[f"cw_meal_sel_{d}"]
            st.session_state.cw_meals = _shuffle_meals_for_days(
                pool, day_names, existing=st.session_state.cw_meals
            )
            st.rerun()

    st.markdown("---")
    for d in day_names:
        current = st.session_state.cw_meals.get(d, "")
        options = pool[:] if pool else ["(add meals to your Meal Library)"]
        if current and current not in options:
            options = [current] + options

        c1, c2, c3 = st.columns([1, 4, 1])
        with c1:
            st.markdown(f"<div class='day-label' style='padding-top:0.6rem;'>{d}</div>", unsafe_allow_html=True)
        with c2:
            idx = options.index(current) if current in options else 0
            choice = st.selectbox(
                f"{d} dinner", options, index=idx, key=f"cw_meal_sel_{d}",
                label_visibility="collapsed",
            )
            st.session_state.cw_meals[d] = choice
        with c3:
            if st.button("🎲", key=f"cw_meal_reroll_{d}", help=f"Reroll {d}'s dinner"):
                if pool:
                    if f"cw_meal_sel_{d}" in st.session_state:
                        del st.session_state[f"cw_meal_sel_{d}"]
                    st.session_state.cw_meals[d] = random.choice(pool)
                    st.rerun()

    st.markdown("---")
    if st.button("✅ Approve Meals"):
        st.session_state.cw_meals_approved = True
        st.success("Meals approved. Move on to the Tasks tab →")


# ── Phase 2: Tasks ──────────────────────────────────────────────────────
def _tasks_phase(task_df):
    if not st.session_state.cw_boundaries_set:
        st.warning("Set your week's boundaries first (📅 Boundaries tab).")
        return

    day_names = [name for name, _ in st.session_state.cw_active_days]

    avail = available_tasks(task_df)
    avail_names = avail["Task Name"].tolist()

    st.session_state.cw_selected_tasks = st.multiselect(
        "Which tasks are in play this week?",
        options=avail_names,
        default=[t for t in st.session_state.cw_selected_tasks if t in avail_names],
    )

    with st.expander("➕ Add a new task"):
        name = st.text_input("Task Name", key="cw_new_task_name")
        desc = st.text_input("Description (optional)", key="cw_new_task_desc")
        due = st.date_input("Due date (optional)", value=None, key="cw_new_task_due")
        if st.button("Add task", key="cw_add_task_btn"):
            if name.strip():
                new_row = pd.DataFrame([{
                    "Task Name": name.strip(),
                    "Task Description": desc.strip(),
                    "Task Type": "Unscheduled",
                    "Date (If Applicable)": "",
                    "Due Date (If Applicable)": format_date(due) if due else "",
                    "Task Status": "Incomplete",
                    "Completion Date (If Applicable)": "",
                }])
                updated = pd.concat([task_df, new_row], ignore_index=True)
                save_task_library(updated)
                st.success(f"Added '{name.strip()}' to the Task Library.")
                st.rerun()
            else:
                st.warning("Enter a task name first.")

    st.markdown("---")
    if st.button("🎲 Shuffle Selected Tasks Into Days"):
        existing = {
            d: [t for t in st.session_state.cw_tasks_by_day.get(d, []) if t in st.session_state.cw_selected_tasks]
            for d in day_names
        }
        st.session_state.cw_tasks_by_day = _shuffle_tasks_for_days(
            st.session_state.cw_selected_tasks, day_names, existing=existing
        )
        st.rerun()

    st.caption("Reassign any task to a different day below.")
    new_by_day = {}
    for d in day_names:
        current = [t for t in st.session_state.cw_tasks_by_day.get(d, []) if t in st.session_state.cw_selected_tasks]
        chosen = st.multiselect(
            d, options=st.session_state.cw_selected_tasks, default=current, key=f"cw_task_day_{d}",
        )
        new_by_day[d] = chosen
    st.session_state.cw_tasks_by_day = new_by_day

    assigned = {t for tasks in new_by_day.values() for t in tasks}
    unassigned = [t for t in st.session_state.cw_selected_tasks if t not in assigned]
    if unassigned:
        st.warning(f"Not yet assigned to a day: {', '.join(unassigned)}")

    st.markdown("---")
    if st.button("✅ Approve Tasks"):
        st.session_state.cw_tasks_approved = True
        st.success("Tasks approved. Move on to the Aims tab →")


# ── Phase 3: Aims ────────────────────────────────────────────────────────
def _aims_phase():
    st.session_state.cw_isaac_aim = st.text_area(
        "Isaac's Aim", value=st.session_state.cw_isaac_aim, height=90
    )
    st.session_state.cw_madison_aim = st.text_area(
        "Madison's Aim", value=st.session_state.cw_madison_aim, height=90
    )
    st.session_state.cw_family_aim = st.text_area(
        "Family Aim", value=st.session_state.cw_family_aim, height=90
    )


# ── Phase 4: Save ────────────────────────────────────────────────────────
def _save_phase(task_df, view_df):
    if not st.session_state.cw_boundaries_set:
        st.warning("Set your week's boundaries first (📅 Boundaries tab).")
        return

    active_days = st.session_state.cw_active_days
    day_names = [name for name, _ in active_days]
    date_by_day = {name: d for name, d in active_days}

    range_label = f"{format_date(active_days[0][1])} – {format_date(active_days[-1][1])}"
    st.markdown(f"**Week of:** {range_label}")

    st.markdown("---")
    st.subheader("Preview")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Dinners**")
        for d in day_names:
            st.write(f"- {d}: {st.session_state.cw_meals.get(d, '_unset_')}")
    with c2:
        st.markdown("**Tasks**")
        any_task = False
        for d in day_names:
            for t in st.session_state.cw_tasks_by_day.get(d, []):
                any_task = True
                st.write(f"- {d}: {t}")
        if not any_task:
            st.caption("_No tasks scheduled._")
        st.markdown("**Aims**")
        st.write(f"Isaac: {st.session_state.cw_isaac_aim or '_none_'}")
        st.write(f"Madison: {st.session_state.cw_madison_aim or '_none_'}")
        st.write(f"Family: {st.session_state.cw_family_aim or '_none_'}")

    if not st.session_state.cw_meals_approved:
        st.warning("Meals haven't been approved yet (Meals tab).")
    if not st.session_state.cw_tasks_approved and any(st.session_state.cw_tasks_by_day.values()):
        st.warning("Tasks haven't been approved yet (Tasks tab).")

    st.markdown("---")
    if st.button("💾 Save This Week", type="primary"):
        row = {"Dates of Week": range_label}
        for d in day_names:
            row[f"{d} Dinner"] = st.session_state.cw_meals.get(d, "")
        row["Isaac Aim"] = st.session_state.cw_isaac_aim
        row["Madison Aim"] = st.session_state.cw_madison_aim
        row["Family Aim"] = st.session_state.cw_family_aim
        for d in day_names:
            row[f"{d} Tasks"] = join_tasks(st.session_state.cw_tasks_by_day.get(d, []))
        row["Isaac Reflection"] = ""
        row["Madison Reflection"] = ""
        row["Family Reflection"] = ""
        row["Carryover Meals"] = ""

        updated_view = pd.concat([view_df, pd.DataFrame([row])], ignore_index=True)
        save_view_weeks(updated_view)

        updated_tasks = task_df.copy()
        for d in day_names:
            for t in st.session_state.cw_tasks_by_day.get(d, []):
                mask = updated_tasks["Task Name"] == t
                if mask.any():
                    idx = updated_tasks[mask].index[0]
                    updated_tasks.loc[idx, "Date (If Applicable)"] = format_date(date_by_day[d])
                    updated_tasks.loc[idx, "Task Type"] = "Scheduled"
        save_task_library(updated_tasks)

        st.success("Week saved! Find it in the Week Library.")
        st.balloons()
        _reset_wizard()
