"""
Smart Expense Tracker
A local, persistent expense tracker built with Streamlit, SQLite, Pandas and Plotly.

Run:
    pip install -r requirements.txt
    streamlit run main.py

Data is stored in smart_expenses.db beside this file.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------ Configuration ------------------------------

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "smart_expenses.db"
CATEGORIES = ["Food", "Travel", "Shopping", "Study"]
CURRENCY = "₹"

st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------ Database layer -----------------------------


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection and always close it."""
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    """Create database tables and indexes on first run."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL
                    CHECK(category IN ('Food', 'Travel', 'Shopping', 'Study')),
                amount REAL NOT NULL CHECK(amount > 0),
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)"
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO settings(setting_key, setting_value)
            VALUES ('monthly_budget', '10000')
            """
        )


def get_budget() -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT setting_value FROM settings WHERE setting_key = 'monthly_budget'"
        ).fetchone()
    return float(row["setting_value"]) if row else 10000.0


def save_budget(value: float) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO settings(setting_key, setting_value)
            VALUES ('monthly_budget', ?)
            ON CONFLICT(setting_key)
            DO UPDATE SET setting_value = excluded.setting_value
            """,
            (str(float(value)),),
        )


def add_expense(expense_date: date, category: str, amount: float, note: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO expenses(expense_date, category, amount, note)
            VALUES (?, ?, ?, ?)
            """,
            (expense_date.isoformat(), category, float(amount), note.strip()),
        )


def update_expense(
    expense_id: int, expense_date: date, category: str, amount: float, note: str
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE expenses
            SET expense_date = ?, category = ?, amount = ?, note = ?
            WHERE id = ?
            """,
            (expense_date.isoformat(), category, float(amount), note.strip(), expense_id),
        )


def delete_expense(expense_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))


def fetch_expenses() -> pd.DataFrame:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, expense_date AS Date, category AS Category,
                   amount AS Amount, note AS Note
            FROM expenses
            ORDER BY expense_date DESC, id DESC
            """
        ).fetchall()
    df = pd.DataFrame([dict(row) for row in rows])
    if df.empty:
        return pd.DataFrame(
            columns=["id", "Date", "Category", "Amount", "Note"]
        )
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
    return df


# ------------------------------ Helper functions ---------------------------


def money(value: float) -> str:
    return f"{CURRENCY}{value:,.2f}"


def month_bounds(selected_month: date) -> tuple[date, date]:
    first_day = selected_month.replace(day=1)
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1)
    return first_day, next_month - timedelta(days=1)


def style_page() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.6rem; padding-bottom: 2.5rem;}
        div[data-testid="stMetric"] {
            background: var(--secondary-background-color);
            border: 1px solid rgba(128,128,128,.18);
            padding: 14px 16px;
            border-radius: 12px;
        }
        .small-muted {color: var(--text-color); opacity: .72; font-size: .9rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------ App interface -------------------------------

initialize_database()
style_page()

st.title("💸 Smart Expense Tracker")
st.caption("A simple personal finance dashboard. Your data is saved locally on this device.")

all_expenses = fetch_expenses()
today = date.today()
current_month_start, current_month_end = month_bounds(today)

# Sidebar: budget, add, edit and delete
with st.sidebar:
    st.header("⚙️ Settings")
    current_budget = get_budget()
    new_budget = st.number_input(
        "Monthly budget",
        min_value=0.0,
        value=float(current_budget),
        step=500.0,
        format="%.2f",
        help="This budget is saved in the local database.",
    )
    if st.button("Save budget", use_container_width=True):
        save_budget(new_budget)
        st.success("Budget saved.")
        st.rerun()

    st.divider()
    st.header("➕ Add expense")
    with st.form("add_expense_form", clear_on_submit=True):
        add_date = st.date_input("Date", value=today, key="add_date")
        add_category = st.selectbox("Category", CATEGORIES, key="add_category")
        add_amount = st.number_input(
            "Amount (₹)", min_value=0.01, value=100.0, step=10.0, key="add_amount"
        )
        add_note = st.text_input(
            "Note (optional)", max_chars=120, placeholder="e.g. Lunch, bus ticket"
        )
        add_submitted = st.form_submit_button(
            "Add expense", type="primary", use_container_width=True
        )
        if add_submitted:
            add_expense(add_date, add_category, add_amount, add_note)
            st.success("Expense saved successfully.")
            st.rerun()

    st.divider()
    st.header("🛠️ Manage expenses")
    if all_expenses.empty:
        st.caption("Add an expense before editing or deleting records.")
    else:
        id_options = all_expenses["id"].astype(int).tolist()
        selected_id = st.selectbox(
            "Select expense ID",
            id_options,
            format_func=lambda expense_id: (
                f"#{expense_id} · "
                f"{all_expenses.loc[all_expenses['id'] == expense_id, 'Date'].iloc[0].date()} · "
                f"{all_expenses.loc[all_expenses['id'] == expense_id, 'Category'].iloc[0]} · "
                f"{money(float(all_expenses.loc[all_expenses['id'] == expense_id, 'Amount'].iloc[0]))}"
            ),
        )
        selected_row = all_expenses.loc[all_expenses["id"] == selected_id].iloc[0]

        with st.expander("Edit selected expense"):
            with st.form("edit_expense_form"):
                edit_date = st.date_input(
                    "Date",
                    value=selected_row["Date"].date(),
                    key=f"edit_date_{selected_id}",
                )
                edit_category = st.selectbox(
                    "Category",
                    CATEGORIES,
                    index=CATEGORIES.index(selected_row["Category"]),
                    key=f"edit_category_{selected_id}",
                )
                edit_amount = st.number_input(
                    "Amount (₹)",
                    min_value=0.01,
                    value=float(selected_row["Amount"]),
                    step=10.0,
                    key=f"edit_amount_{selected_id}",
                )
                edit_note = st.text_input(
                    "Note",
                    value=str(selected_row["Note"]),
                    max_chars=120,
                    key=f"edit_note_{selected_id}",
                )
                edit_submitted = st.form_submit_button(
                    "Save changes", use_container_width=True
                )
                if edit_submitted:
                    update_expense(
                        int(selected_id),
                        edit_date,
                        edit_category,
                        edit_amount,
                        edit_note,
                    )
                    st.success("Expense updated.")
                    st.rerun()

        with st.expander("Delete selected expense"):
            st.warning("Deleting a record is permanent.")
            confirm_delete = st.checkbox(
                f"I want to permanently delete expense #{selected_id}",
                key=f"confirm_delete_{selected_id}",
            )
            if st.button(
                "Delete expense",
                type="secondary",
                disabled=not confirm_delete,
                use_container_width=True,
            ):
                delete_expense(int(selected_id))
                st.success("Expense deleted.")
                st.rerun()

# Main dashboard month selector
st.subheader("📅 Monthly dashboard")
month_col, note_col = st.columns([1, 2])
with month_col:
    selected_month = st.date_input(
        "Choose any date in the month",
        value=today.replace(day=1),
        help="The dashboard totals and budget progress use the selected month.",
    )
with note_col:
    st.markdown(
        '<p class="small-muted">The dashboard below shows the selected month. '
        'Use the filters further down to inspect individual records.</p>',
        unsafe_allow_html=True,
    )

month_start, month_end = month_bounds(selected_month)
monthly = all_expenses[
    (all_expenses["Date"].dt.date >= month_start)
    & (all_expenses["Date"].dt.date <= month_end)
].copy()

monthly_total = float(monthly["Amount"].sum())
budget = get_budget()
remaining = budget - monthly_total
expense_count = len(monthly)
daily_average = monthly_total / max(today.day, 1) if selected_month.month == today.month and selected_month.year == today.year else monthly_total / max((month_end - month_start).days + 1, 1)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Spent this month", money(monthly_total))
m2.metric(
    "Budget remaining",
    money(remaining),
    delta="Over budget" if remaining < 0 else "Within budget",
    delta_color="inverse" if remaining < 0 else "normal",
)
m3.metric("Expenses this month", f"{expense_count}")
m4.metric("Average per day", money(daily_average))

if budget > 0:
    progress = monthly_total / budget
    st.progress(min(progress, 1.0), text=f"{progress:.1%} of monthly budget used")
    if remaining < 0:
        st.error(f"You have exceeded your monthly budget by {money(abs(remaining))}.")
    elif progress >= 0.8:
        st.warning("You have used at least 80% of your monthly budget.")
else:
    st.info("Your monthly budget is set to ₹0. Add a budget in the sidebar to track progress.")

st.divider()

# Charts
chart_left, chart_right = st.columns(2)
with chart_left:
    st.markdown("#### 🥧 Spending by category")
    if monthly.empty:
        st.info("No expenses recorded for this month yet.")
    else:
        category_summary = (
            monthly.groupby("Category", as_index=False)["Amount"]
            .sum()
            .sort_values("Amount", ascending=False)
        )
        pie = px.pie(
            category_summary,
            names="Category",
            values="Amount",
            hole=0.42,
            title=f"Category breakdown · {selected_month.strftime('%B %Y')}",
        )
        pie.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="%{label}<br>₹%{value:,.2f}<extra></extra>",
        )
        pie.update_layout(margin=dict(t=55, b=10, l=10, r=10), legend_title_text="")
        st.plotly_chart(pie, use_container_width=True)

with chart_right:
    st.markdown("#### 📈 Spending by day")
    if monthly.empty:
        st.info("A daily spending chart will appear when you add expenses.")
    else:
        daily_summary = (
            monthly.assign(Day=monthly["Date"].dt.date)
            .groupby("Day", as_index=False)["Amount"]
            .sum()
        )
        daily_chart = px.bar(
            daily_summary,
            x="Day",
            y="Amount",
            title="Daily expense total",
            labels={"Day": "Date", "Amount": "Amount (₹)"},
        )
        daily_chart.update_layout(
            margin=dict(t=55, b=10, l=10, r=10),
            xaxis_title="Date",
            yaxis_title="Amount (₹)",
        )
        st.plotly_chart(daily_chart, use_container_width=True)

# Full records, filters and CSV
st.divider()
st.subheader("📋 All expense records")

filter1, filter2, filter3 = st.columns([1, 1, 1])
with filter1:
    category_filter = st.selectbox("Category filter", ["All"] + CATEGORIES)
with filter2:
    default_from = all_expenses["Date"].min().date() if not all_expenses.empty else today
    date_from = st.date_input("From date", value=default_from, key="filter_from")
with filter3:
    date_to = st.date_input("To date", value=today, key="filter_to")

if date_from > date_to:
    st.error("'From date' cannot be later than 'To date'.")
    filtered = all_expenses.iloc[0:0].copy()
else:
    filtered = all_expenses[
        (all_expenses["Date"].dt.date >= date_from)
        & (all_expenses["Date"].dt.date <= date_to)
    ].copy()
    if category_filter != "All":
        filtered = filtered[filtered["Category"] == category_filter]

if filtered.empty:
    st.info("No expenses match the selected filters.")
else:
    display = filtered.copy()
    display["Date"] = display["Date"].dt.strftime("%d %b %Y")
    display["Amount"] = display["Amount"].map(money)
    display = display.rename(columns={"id": "ID", "Note": "Description"})
    st.dataframe(
        display[["ID", "Date", "Category", "Amount", "Description"]],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Showing {len(filtered)} expense record(s), total {money(float(filtered['Amount'].sum()))}.")

csv_export = filtered.copy()
if not csv_export.empty:
    csv_export["Date"] = csv_export["Date"].dt.strftime("%Y-%m-%d")
csv_export = csv_export.rename(
    columns={"id": "ID", "Date": "Date", "Category": "Category",
             "Amount": "Amount_INR", "Note": "Description"}
)
csv_bytes = csv_export.to_csv(index=False).encode("utf-8-sig")

download_col, all_col = st.columns([1, 2])
with download_col:
    st.download_button(
        "⬇️ Download filtered CSV",
        data=csv_bytes,
        file_name=f"expenses_{date_from}_{date_to}.csv",
        mime="text/csv",
        disabled=filtered.empty,
        use_container_width=True,
    )
with all_col:
    st.caption("CSV export follows the category and date filters currently selected.")

with st.expander("ℹ️ About data storage and backup"):
    st.write(
        "Your expenses and budget are stored in the SQLite database file "
        "`smart_expenses.db` in the same folder as `main.py`. The database "
        "persists when you close or restart the app. Back up that file regularly "
        "if you want to keep your records safe. Do not delete it unless you want "
        "to reset your data."
    )

st.caption("Smart Expense Tracker · Built with Streamlit, SQLite, Pandas and Plotly")
