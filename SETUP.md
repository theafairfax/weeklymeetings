# Setup

## 1. Prep your Google Sheet
This app expects **one spreadsheet with three tabs**, named exactly:

- `Meal Library` — columns: `Protein`, `Side`, `Course`
- `Task Library` — columns: `Task Name`, `Task Description`, `Task Type`,
  `Date (If Applicable)`, `Due Date (If Applicable)`, `Task Status`,
  `Completion Date (If Applicable)`
- `View Weeks` — columns: `Dates of Week`, `Monday Dinner` … `Sunday Dinner`,
  `Isaac Aim`, `Madison Aim`, `Family Aim`, `Monday Tasks` … `Sunday Tasks`

If your existing tabs are named differently, just edit `MEAL_WS`, `TASK_WS`,
and `VIEW_WS` at the top of `sheets.py` to match.

The app will automatically add four columns to `View Weeks` the first time
you save a week if they're not already there: `Isaac Reflection`,
`Madison Reflection`, `Family Reflection`, `Carryover Meals`. You can add
them yourself ahead of time if you'd rather control the column order.

## 2. Create a Google service account
1. Go to the [Google Cloud Console](https://console.cloud.google.com/), create
   (or reuse) a project.
2. Enable the **Google Sheets API** and **Google Drive API**.
3. Under *APIs & Services → Credentials*, create a **Service Account**.
4. Open the service account, go to **Keys → Add Key → Create new key → JSON**,
   and download it.
5. Open your Google Sheet and **Share** it with the service account's email
   address (found in the JSON as `client_email`), giving it **Editor** access.

## 3. Add your secrets
Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill
in the values from the JSON key you downloaded, plus your spreadsheet's URL
as `spreadsheet`.

- **Running locally:** just save the file at `.streamlit/secrets.toml`.
- **Streamlit Community Cloud:** paste the same contents into your app's
  *Settings → Secrets*.

`secrets.toml` is already covered by `.gitignore`-style caution — never
commit your real key to a public repo.

## 4. Install & run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes on how data flows
- **Meal Library** stores raw ingredients/components, not fixed meals. The
  app builds every Protein × Side combo plus every standalone Course into a
  pool to shuffle from — add to the library any time from the Meals tab.
- **Task Library** is the single source of truth for tasks. A task is
  "available" to place into a new week as long as its `Task Status` isn't
  `Complete` — so unscheduled backlog items and rolled-over incomplete tasks
  both resurface automatically.
- **View Weeks** holds one row per week. Task cells store multiple tasks
  joined with `; `.
