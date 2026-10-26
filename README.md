# SpendWise — Personal Expense Analytics

A beginner-friendly college project using Python, Flask, Pandas, SQLite, HTML, CSS, JavaScript, and Plotly.

## Features
- CSV and Excel expense import with basic cleaning
- SQLite storage and transaction listing/search/delete
- Manual expense entry
- Dashboard totals and monthly/category charts
- Histogram, boxplot, bar chart, scatter plot and trendline
- Monthly totals, 3-month moving average, optional ARIMA forecast
- Monthly category report and CSV export

## Requirements
- Python 3.10 or newer recommended
- Internet connection for Plotly and Google Fonts CDN assets

## Run on Windows
1. Extract the ZIP.
2. Open the extracted `SpendWise` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:
   `python -m venv venv`
5. Activate it:
   PowerShell: `.\venv\Scripts\Activate.ps1`
   Command Prompt: `venv\Scripts\activate`
6. Install packages:
   `pip install -r requirements.txt`
7. Run:
   `python app.py`
8. Open in a browser:
   `http://127.0.0.1:5000`

## Run on macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Then open `http://127.0.0.1:5000`.

## Sample data
Use `static/sample_expenses.csv` from the Transactions page or upload it directly.

## Upload format
Required columns: `date`, `category`, `amount`.
Optional columns: `description`, `payment_method`.
Dates should be parseable by Pandas. Amounts should be non-negative numbers.

## Lab mapping
- Lab 5: file extraction, cleaning and SQLite storage
- Lab 6: monthly trends, moving average and optional ARIMA forecasting
- Lab 7: trend and correlation-style scatter visualization with trendline
- Lab 8: histogram, boxplot, bar chart and donut chart

## Notes
- The forecast is educational and should not be treated as financial advice.
- For a public deployment, change `app.secret_key`, disable debug mode, and use a persistent database.
- This starter project is intended for local college demonstration, not production use.
