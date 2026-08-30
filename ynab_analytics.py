"""
ynab_analytics.py — YNAB-powered financial dashboard and inflow allocation workflow.
"""
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st


ALLOCATION_RULES = {
    "Tax": 0.05,
    "Roth IRA": 0.07,
    "Savings": 0.18,
    "Stock Market": 0.07,
    "Isaac Personal": 0.02,
    "Madison Personal": 0.02,
    "Travel": 0.09,
}

TEMP_SAVINGS_CATEGORIES = ("Tax", "Roth IRA", "Savings")


def _request_json(url: str, headers: dict) -> dict:
    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code != 200:
        raise RuntimeError(f"YNAB API request failed ({response.status_code}): {response.text}")
    return response.json()["data"]


def _fetch_recent_inflows(base_url: str, budget_id: str, headers: dict) -> pd.DataFrame:
    """Return recent positive, non-transfer YNAB transactions as candidate inflows."""
    since_date = (date.today() - timedelta(days=21)).isoformat()
    data = _request_json(
        f"{base_url}/budgets/{budget_id}/transactions?since_date={since_date}",
        headers,
    )

    rows = []
    for tx in data.get("transactions", []):
        amount = tx.get("amount", 0) / 1000.0
        if amount <= 0 or tx.get("deleted", False):
            continue

        payee = tx.get("payee_name") or "Unknown payee"
        if payee.lower().startswith("transfer"):
            continue

        rows.append(
            {
                "id": tx.get("id", ""),
                "date": tx.get("date", ""),
                "payee": payee,
                "memo": tx.get("memo") or "",
                "account": tx.get("account_name") or "",
                "amount": amount,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["id", "date", "payee", "memo", "account", "amount"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values(["date", "amount"], ascending=[False, False]).reset_index(drop=True)
    return df


def _render_allocation(amount: float) -> None:
    allocations = {name: round(amount * pct, 2) for name, pct in ALLOCATION_RULES.items()}
    allocated_total = round(sum(allocations.values()), 2)
    unallocated = round(amount - allocated_total, 2)
    temporary_savings = round(sum(allocations[name] for name in TEMP_SAVINGS_CATEGORIES), 2)

    st.markdown("### Allocation Plan")
    st.caption("Calculated from the approved inflow amount using your fixed percentage rules.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Approved inflow", f"${amount:,.2f}")
    with c2:
        st.metric("Temporarily held in savings", f"${temporary_savings:,.2f}")
    with c3:
        st.metric("Unallocated remainder", f"${unallocated:,.2f}")

    st.info(
        "The temporary savings figure combines **Tax + Roth IRA + Savings** because those funds are initially housed together in savings before being distributed further."
    )

    display_rows = [
        {"Category": "Tax", "Percent": "5%", "Amount": allocations["Tax"]},
        {"Category": "Roth IRA", "Percent": "7%", "Amount": allocations["Roth IRA"]},
        {"Category": "Savings", "Percent": "18%", "Amount": allocations["Savings"]},
        {"Category": "Stock Market", "Percent": "7%", "Amount": allocations["Stock Market"]},
        {"Category": "Isaac Personal", "Percent": "2%", "Amount": allocations["Isaac Personal"]},
        {"Category": "Madison Personal", "Percent": "2%", "Amount": allocations["Madison Personal"]},
        {"Category": "Travel", "Percent": "9%", "Amount": allocations["Travel"]},
    ]
    allocation_df = pd.DataFrame(display_rows)
    allocation_df["Amount"] = allocation_df["Amount"].map(lambda x: f"${x:,.2f}")
    st.dataframe(allocation_df, use_container_width=True, hide_index=True)

    st.markdown("#### Savings-account staging detail")
    savings_rows = pd.DataFrame(
        [
            {"Component": "Tax", "Amount": f"${allocations['Tax']:,.2f}"},
            {"Component": "Roth IRA", "Amount": f"${allocations['Roth IRA']:,.2f}"},
            {"Component": "Savings", "Amount": f"${allocations['Savings']:,.2f}"},
            {"Component": "Combined temporary savings balance", "Amount": f"${temporary_savings:,.2f}"},
        ]
    )
    st.dataframe(savings_rows, use_container_width=True, hide_index=True)


def render():
    st.title("💰 Financial Dashboard")
    st.caption("Detect recent YNAB inflow, approve or correct it, then subdivide it into your household allocation buckets.")

    if "ynab" not in st.secrets or "api_token" not in st.secrets["ynab"]:
        st.error(
            "Missing YNAB configuration. Add your `api_token` under a `[ynab]` section inside `.streamlit/secrets.toml`."
        )
        return

    api_token = st.secrets["ynab"]["api_token"]
    base_url = "https://api.ynab.com/v1"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        with st.spinner("Fetching YNAB budgets..."):
            budgets = _request_json(f"{base_url}/budgets", headers).get("budgets", [])
    except Exception as e:
        st.error(f"Could not connect to YNAB: {e}")
        return

    if not budgets:
        st.warning("No budgets found for this YNAB token.")
        return

    budget_map = {b["name"]: b["id"] for b in budgets}
    selected_budget = st.selectbox("Select Budget Profile", list(budget_map.keys()))
    budget_id = budget_map[selected_budget]

    st.markdown("---")
    st.subheader("1 · Detect inflow")
    st.caption("Recent positive, non-transfer YNAB transactions are shown as candidate inflows.")

    try:
        with st.spinner("Checking recent YNAB inflows..."):
            inflows = _fetch_recent_inflows(base_url, budget_id, headers)
    except Exception as e:
        st.error(f"Could not fetch recent transactions: {e}")
        return

    if inflows.empty:
        st.warning("No recent positive inflow transactions were found in the last 21 days.")
        detected_amount = 0.0
    else:
        inflow_options = {}
        for idx, row in inflows.iterrows():
            label = (
                f"{row['date'].date().isoformat()} · {row['payee']} · "
                f"${row['amount']:,.2f} · {row['account']}"
            )
            inflow_options[label] = idx

        selected_label = st.selectbox("Detected inflow", list(inflow_options.keys()))
        selected_row = inflows.loc[inflow_options[selected_label]]
        detected_amount = float(selected_row["amount"])

        detail_cols = st.columns(3)
        detail_cols[0].metric("Detected amount", f"${detected_amount:,.2f}")
        detail_cols[1].metric("Account", selected_row["account"] or "—")
        detail_cols[2].metric("Payee", selected_row["payee"] or "—")
        if selected_row["memo"]:
            st.caption(f"Memo: {selected_row['memo']}")

    st.markdown("---")
    st.subheader("2 · Approve or correct")
    approved_amount = st.number_input(
        "Approved inflow amount",
        min_value=0.0,
        value=float(detected_amount),
        step=1.0,
        format="%.2f",
        help="Leave this as detected, or manually change it if the YNAB transaction does not match the amount you want to allocate.",
    )

    if detected_amount > 0:
        difference = round(approved_amount - detected_amount, 2)
        if difference != 0:
            st.caption(f"Manual adjustment from detected inflow: {difference:+,.2f}")

    st.markdown("---")
    st.subheader("3 · Subdivide inflow")
    st.caption(
        "Tax 5% · Roth IRA 7% · Savings 18% · Stock Market 7% · Isaac Personal 2% · Madison Personal 2% · Travel 9%"
    )

    if st.button("💸 Calculate Allocation", use_container_width=True, type="primary"):
        if approved_amount <= 0:
            st.warning("Enter or approve an inflow amount greater than $0 first.")
        else:
            st.session_state["ynab_last_approved_inflow"] = float(approved_amount)

    if st.session_state.get("ynab_last_approved_inflow", 0) > 0:
        _render_allocation(float(st.session_state["ynab_last_approved_inflow"]))

    st.markdown("---")
    with st.expander("📊 Existing financial overview"):
        try:
            with st.spinner("Fetching account and monthly summary data..."):
                accounts = _request_json(f"{base_url}/budgets/{budget_id}/accounts", headers).get("accounts", [])
                months_data = _request_json(f"{base_url}/budgets/{budget_id}/months", headers).get("months", [])

            net_worth = sum(
                a.get("balance", 0)
                for a in accounts
                if not a.get("deleted", False) and not a.get("closed", False)
            ) / 1000.0

            history = []
            for month in months_data:
                history.append(
                    {
                        "Month": month["month"][:7],
                        "Income": month.get("income", 0) / 1000.0,
                        "Spending": abs(month.get("activity", 0)) / 1000.0,
                    }
                )

            df_history = pd.DataFrame(history)
            current_income = df_history["Income"].iloc[-1] if not df_history.empty else 0.0
            avg_spending = df_history["Spending"].tail(3).mean() if not df_history.empty else 0.0

            col1, col2, col3 = st.columns(3)
            col1.metric("Net Worth", f"${net_worth:,.2f}")
            col2.metric("Current Month Income", f"${current_income:,.2f}")
            col3.metric("3-Month Spending Avg", f"${avg_spending:,.2f}")

            if not df_history.empty:
                chart_data = df_history.set_index("Month")
                st.bar_chart(chart_data[["Income", "Spending"]])
                st.dataframe(df_history, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"Could not load the legacy financial overview: {e}")
