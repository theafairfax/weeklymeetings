import streamlit as st
import requests
import pandas as pd

class YNABClient:
    def __init__(self):
        self.token = st.secrets["ynab"]["api_token"]
        self.base_url = "https://api.ynab.com/v1"
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def get_budgets(self):
        """Fetches all available budgets."""
        response = requests.get(f"{self.base_url}/budgets", headers=self.headers)
        if response.status_code == 200:
            return response.json()["data"]["budgets"]
        else:
            st.error(f"Failed to fetch budgets: {response.text}")
            return []

    def get_financial_metrics(self, budget_id):
        """Calculates net worth, current month income, and spending averages."""
        # 1. Fetch Accounts for Net Worth
        accts_res = requests.get(f"{self.base_url}/budgets/{budget_id}/accounts", headers=self.headers)
        net_worth = 0.0
        
        if accts_res.status_code == 200:
            accounts = accts_res.json()["data"]["accounts"]
            # Sum balances of all non-deleted, open accounts
            net_worth = sum(a["balance"] for a in accounts if not a["deleted"] and not a["closed"]) / 1000.0

        # 2. Fetch Budget Months for Trends
        months_res = requests.get(f"{self.base_url}/budgets/{budget_id}/months", headers=self.headers)
        metrics = {
            "net_worth": net_worth,
            "current_income": 0.0,
            "avg_spending": 0.0,
            "history_df": pd.DataFrame()
        }

        if months_res.status_code == 200:
            months_data = months_res.json()["data"]["months"]
            
            # Build history for visualization
            history = []
            for m in months_data:
                # YNAB values are in milliunits
                inc = m.get("income", 0) / 1000.0
                exp = abs(m.get("activity", 0)) / 1000.0
                history.append({
                    "Month": m["month"][:7], # YYYY-MM
                    "Income": inc,
                    "Spending": exp
                })
            
            df = pd.DataFrame(history)
            metrics["history_df"] = df
            
            # Pull current month metrics (most recent month entry)
            if history:
                metrics["current_income"] = history[-1]["Income"]
                # Calculate average spending across the last 3 active months
                metrics["avg_spending"] = df["Spending"].tail(3).mean()

        return metrics
