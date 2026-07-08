"""
ynab_analytics.py — pull live data from the YNAB API to display financial health indicators.
"""
import streamlit as st
import requests
import pandas as pd

def render():
    st.title("💰 Financial Analytics")
    st.caption("Live financial performance overview fetched from your YNAB budget profile.")

    # Validate secrets configuration
    if "ynab" not in st.secrets or "api_token" not in st.secrets["ynab"]:
        st.error("Missing YNAB configuration. Please add your `api_token` under a `[ynab]` section inside `.streamlit/secrets.toml`.")
        return

    api_token = st.secrets["ynab"]["api_token"]
    base_url = "https://api.ynab.com/v1"
    headers = {"Authorization": f"Bearer {api_token}"}

    # 1. Fetch available budgets
    try:
        with st.spinner("Fetching budgets..."):
            res = requests.get(f"{base_url}/budgets", headers=headers)
        if res.status_code != 200:
            st.error(f"Failed to fetch budgets from YNAB API: {res.text}")
            return
        budgets = res.json()["data"]["budgets"]
    except Exception as e:
        st.error(f"Error connecting to YNAB API: {e}")
        return

    if not budgets:
        st.warning("No budgets found associated with this YNAB token.")
        return

    # Select budget profile
    budget_map = {b["name"]: b["id"] for b in budgets}
    selected_budget = st.selectbox("Select Budget Profile", list(budget_map.keys()))
    budget_id = budget_map[selected_budget]

    # 2. Fetch Accounts and Budget Month summary details
    try:
        with st.spinner("Streaming financial metrics..."):
            accts_res = requests.get(f"{base_url}/budgets/{budget_id}/accounts", headers=headers)
            months_res = requests.get(f"{base_url}/budgets/{budget_id}/months", headers=headers)
    except Exception as e:
        st.error(f"Failed to stream budget analytical data: {e}")
        return

    # Process Net Worth from open accounts
    net_worth = 0.0
    if accts_res.status_code == 200:
        accounts = accts_res.json()["data"]["accounts"]
        # Filter for open and non-deleted accounts
        net_worth = sum(a["balance"] for a in accounts if not a["deleted"] and not a["closed"]) / 1000.0
    else:
        st.warning("Could not pull account details for Net Worth calculations.")

    # Process Historical trends, Current Income, and Monthly Average Spending
    current_income = 0.0
    avg_spending = 0.0
    df_history = pd.DataFrame()

    if months_res.status_code == 200:
        months_data = months_res.json()["data"]["months"]
        history = []
        for m in months_data:
            inc = m.get("income", 0) / 1000.0
            # Activity is represented as negative numbers for outflow spending
            exp = abs(m.get("activity", 0)) / 1000.0
            history.append({
                "Month": m["month"][:7],  # formats to YYYY-MM
                "Income": inc,
                "Spending": exp
            })
        
        df_history = pd.DataFrame(history)
        if not df_history.empty:
            current_income = df_history["Income"].iloc[-1]
            # Calculate rolling average using the last 3 active tracking entries
            avg_spending = df_history["Spending"].tail(3).mean()

    # ── Display Layout ─────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-card'><div class='day-label'>Net Worth</div><h3>${net_worth:,.2f}</h3></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><div class='day-label'>Current Month Income</div><h3>${current_income:,.2f}</h3></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><div class='day-label'>3-Month Spending Avg</div><h3>${avg_spending:,.2f}</h3></div>", unsafe_allow_html=True)

    if not df_history.empty:
        st.markdown("<br><div class='day-label'>Cash Flow Trends</div>", unsafe_allow_html=True)
        chart_data = df_history.set_index("Month")
        st.bar_chart(chart_data[["Income", "Spending"]])

        with st.expander("📊 View Historical Data Summary"):
            st.dataframe(df_history, use_container_width=True)
