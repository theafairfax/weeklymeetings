"""
logic.py — pure data helpers for the Weekly Meetings app.
Kept free of Streamlit calls so it can be unit-tested on its own.
"""
import random
from datetime import date, timedelta, datetime

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── Meals ─────────────────────────────────────────────────────────────────
def build_meal_pool(meal_df):
    """Every meal a household could eat: each Protein x each Side combo,
    plus every standalone Course. Returns a sorted list of unique strings."""
    proteins = sorted({p.strip() for p in meal_df["Protein"].tolist() if p.strip()})
    sides = sorted({s.strip() for s in meal_df["Side"].tolist() if s.strip()})
    courses = sorted({c.strip() for c in meal_df["Course"].tolist() if c.strip()})

    pool = list(courses)
    if sides:
        pool += [f"{p} & {s}" for p in proteins for s in sides]
    else:
        pool += proteins
    return sorted(set(pool))


def shuffle_meals(pool, days=None, carryover=None, existing=None):
    """Return a dict {day: meal} for the given `days` (defaults to all 7).
    Carryover meals (list of strings) are placed first, in order, into the
    earliest days. Any days in `existing` that already have a value are
    left untouched (so re-shuffling only fills blanks)."""
    days = days or DAYS
    carryover = [m for m in (carryover or []) if m]
    existing = dict(existing or {})
    result = {}
    remaining_days = []
    for day in days:
        if existing.get(day):
            result[day] = existing[day]
        else:
            remaining_days.append(day)

    co_iter = iter(carryover)
    still_remaining = []
    for day in remaining_days:
        co = next(co_iter, None)
        if co:
            result[day] = co
        else:
            still_remaining.append(day)

    choices = pool[:] if pool else ["(add meals to your Meal Library)"]
    if len(choices) >= len(still_remaining):
        picks = random.sample(choices, len(still_remaining))
    else:
        picks = [random.choice(choices) for _ in still_remaining]
    for day, meal in zip(still_remaining, picks):
        result[day] = meal
    return result


# ── Tasks ────────────────────────────────────────────────────────────────
def available_tasks(task_df):
    """Tasks eligible to be placed into a new week: anything not marked
    Complete (covers the Unscheduled backlog plus rolled-over incomplete
    tasks from prior weeks)."""
    mask = task_df["Task Status"].str.strip().str.lower() != "complete"
    return task_df[mask].copy()


def shuffle_tasks(task_names, days=None, existing=None):
    """Randomly distribute a list of task names across `days` (defaults to
    all 7). Returns {day: [task names]}. Preserves any placements already
    in `existing`."""
    days = days or DAYS
    result = {d: list(v) for d, v in (existing or {}).items() if d in days}
    for d in days:
        result.setdefault(d, [])
    placed = {t for tasks in result.values() for t in tasks}
    todo = [t for t in task_names if t not in placed]
    random.shuffle(todo)
    for i, t in enumerate(todo):
        result[days[i % len(days)]].append(t)
    return result


# ── Weeks / dates ────────────────────────────────────────────────────────
def parse_week_range(dates_str):
    """'6/21/2026 - 6/27/2026' -> (date(2026,6,21), date(2026,6,27)) or None."""
    try:
        start_s, end_s = [s.strip() for s in dates_str.split("-")]
        start = datetime.strptime(start_s, "%m/%d/%Y").date()
        end = datetime.strptime(end_s, "%m/%d/%Y").date()
        return start, end
    except Exception:
        return None


def format_week_range(start: date):
    end = start + timedelta(days=6)
    return f"{start.month}/{start.day}/{start.year} - {end.month}/{end.day}/{end.year}"


def next_monday_after(view_weeks_df):
    """Suggest the start date for a new week: the Monday after the most
    recent week already in the sheet, or the coming Monday if empty."""
    latest = None
    for s in view_weeks_df["Dates of Week"].tolist():
        rng = parse_week_range(s)
        if rng and (latest is None or rng[0] > latest):
            latest = rng[0]
    if latest:
        return latest + timedelta(days=7)
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


def format_date(d: date) -> str:
    return f"{d.month}/{d.day}/{d.year}"


def day_dates(start: date):
    """{'Monday': date, ...} for the 7 days starting at `start` (a Monday)."""
    return {DAYS[i]: start + timedelta(days=i) for i in range(7)}


def split_tasks_cell(cell: str):
    return [t.strip() for t in str(cell).split(";") if t.strip()]


def join_tasks(tasks: list):
    return "; ".join(t for t in tasks if t)
