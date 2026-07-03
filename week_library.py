"""
week_library.py — browse past weekly meetings.
"""
import streamlit as st
from sheets import load_view_weeks
from logic import DAYS, parse_week_range, split_tasks_cell


def render():
    st.title("📚 Week Library")
    st.caption("Every week your household has planned, at a glance.")

    try:
        df = load_view_weeks()
    except Exception as e:
        st.error(f"Couldn't reach the Google Sheet. Check your connection settings in SETUP.md.\n\n{e}")
        return

    if df.empty:
        st.info("No weeks saved yet — head to **Create Week** to plan your first one.")
        return

    # sort newest first
    rows = df.to_dict("records")
    def sort_key(r):
        rng = parse_week_range(r["Dates of Week"])
        return rng[0] if rng else None
    rows = sorted(rows, key=lambda r: (sort_key(r) is None, sort_key(r)), reverse=True)

    search = st.text_input("🔍 Filter by date, meal, task, or aim", "")
    if search:
        s = search.lower()
        rows = [r for r in rows if s in " ".join(str(v) for v in r.values()).lower()]

    st.markdown(f"**{len(rows)}** week(s)")
    st.markdown("---")

    for i, row in enumerate(rows):
        label = row.get("Dates of Week") or "(undated week)"
        with st.expander(f"🗓️ {label}", expanded=(i == 0)):
            col1, col2 = st.columns([1.3, 1])

            with col1:
                st.markdown("<div class='day-label'>Dinners</div>", unsafe_allow_html=True)
                for d in DAYS:
                    meal = row.get(f"{d} Dinner", "")
                    st.markdown(
                        f"<div class='day-card'><b>{d}</b> — {meal or '<i>unset</i>'}</div>",
                        unsafe_allow_html=True,
                    )

            with col2:
                st.markdown("<div class='day-label'>Aims</div>", unsafe_allow_html=True)
                for who in ["Isaac", "Madison", "Family"]:
                    aim = row.get(f"{who} Aim", "")
                    refl = row.get(f"{who} Reflection", "")
                    st.markdown(f"**{who}:** {aim or '_(none set)_'}")
                    if refl:
                        st.caption(f"↳ Reflection: {refl}")

                st.markdown("<div class='day-label' style='margin-top:0.8rem;'>Tasks</div>", unsafe_allow_html=True)
                any_task = False
                for d in DAYS:
                    tasks = split_tasks_cell(row.get(f"{d} Tasks", ""))
                    for t in tasks:
                        any_task = True
                        st.markdown(f"- **{d}:** {t}")
                if not any_task:
                    st.caption("_No tasks scheduled this week._")

                if row.get("Carryover Meals"):
                    st.markdown("<div class='day-label' style='margin-top:0.8rem;'>Carried Over</div>", unsafe_allow_html=True)
                    for m in split_tasks_cell(row.get("Carryover Meals", "")):
                        st.markdown(f"<span class='aim-chip'>🍽️ {m}</span>", unsafe_allow_html=True)
