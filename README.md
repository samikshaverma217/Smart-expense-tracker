# Smart Expense Tracker

A usable local expense-tracking web app built with Python, Streamlit, SQLite, Pandas and Plotly.

## Features

- Add expenses with date, category, amount and optional note
- Categories: Food, Travel, Shopping and Study
- Persistent SQLite storage (data remains after restarting the app)
- Set and save a monthly budget
- Monthly dashboard: total spent, remaining budget, number of expenses and daily average
- Budget progress indicator and overspending warnings
- Plotly category-wise doughnut/pie chart
- Daily spending bar chart
- View all expenses with category and date filters
- Edit and delete saved expenses
- Download filtered records as CSV

## Requirements

- Python 3.9 or newer
- Internet access for the first installation of Python packages

## Run on Windows

1. Extract the project ZIP file.
2. Open Command Prompt or PowerShell inside the extracted `smart_expense_tracker` folder.
3. (Optional but recommended) Create a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the app:

   ```bash
   streamlit run main.py
   ```

## Run on macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run main.py
```

Streamlit will print a local URL, usually `http://localhost:8501`. Open it in your browser.

## Data storage and backup

The app automatically creates `smart_expenses.db` in the project folder the first time it runs. This database stores expenses and your monthly budget. Keep a backup copy of this file to preserve your data.

## Project structure

```text
smart_expense_tracker/
├── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

The SQLite database is created automatically when the app starts; it is not included in the ZIP because each user should have their own data file.
