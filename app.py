"""
app.py — Weekly Meetings entry point.
Navigation: Week Library | Create Week | Review Week | Financial Analytics
"""
import streamlit as st

st.set_page_config(
    page_title="Household Council",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;900&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');

html, body, [class*="css"] {
    font-family: 'Crimson Text', serif;
}
h1, h2, h3 {
    font-family: 'Cinzel', serif !important;
    letter-spacing: 0.05em;
}
.stButton > button {
    font-family: 'Cinzel', serif;
    background: linear-gradient(135deg, #2a1f0e, #3d2b10);
    border: 1px solid #C8A96E;
    color: #C8A96E;
    letter-spacing: 0.1em;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #C8A96E, #a07840);
    color: #0F0F0F;
    border-color: #C8A96E;
}
.stProgress > div > div {
    background: linear-gradient(90deg, #8B4513, #C8A96E) !important;
}
div[data-testid="stSidebar"] {
    background: #111 !important;
    border-right: 1px solid #2a2a2a;
}
.metric-card {
    background: #1A1A1A;
    border: 1px solid #2a2a2a;
    border-left: 3px solid #C8A96E;
    border-radius: 4px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}
.day-card {
    background: #1A1A1A;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
}
.day-label {
    font-family: 'Cinzel', serif;
    color: #C8A96E;
    letter-spacing: 0.08em;
    font-size: 0.85rem;
    text-transform: uppercase;
}
.aim-chip {
    display: inline-block;
    background: #1A1A1A;
    border: 1px solid #C8A96E;
    color: #C8A96E;
    border-radius: 999px;
    padding: 0.15rem 0.8rem;
    margin: 0.1rem;
    font-size: 0.85rem;
}
.week-header {
    font-family: 'Cinzel', serif;
    color: #C8A96E;
    letter-spacing: 0.05em;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📜 Household Council")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["📚 Week Library", "🛠️ Create Week", "🔍 Review Week", "💰 Financial Analytics"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Data lives in your Google Sheet.\nBuilt for Isaac & Madison's weekly meeting.")

# ── Route ─────────────────────────────────────────────────────────────────────
if page == "📚 Week Library":
    import week_library
    week_library.render()
elif page == "🛠️ Create Week":
    import create_week
    create_week.render()
elif page == "🔍 Review Week":
    import review_week
    review_week.render()
elif page == "💰 Financial Analytics":
    import ynab_analytics
    ynab_analytics.render()
