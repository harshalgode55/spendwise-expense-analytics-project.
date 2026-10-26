from pathlib import Path
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "expenses.db"
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                amount REAL NOT NULL CHECK(amount >= 0),
                payment_method TEXT DEFAULT ''
            )
        """)

def ensure_columns(df):
    # Normalize column names and accept a few common alternatives.
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    aliases = {
        "expense_date": "date", "transaction_date": "date",
        "type": "category", "expense_category": "category",
        "details": "description", "note": "description",
        "cost": "amount", "price": "amount",
        "payment": "payment_method", "method": "payment_method"
    }
    df = df.rename(columns={c: aliases[c] for c in df.columns if c in aliases})
    required = {"date", "category", "amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    for optional in ("description", "payment_method"):
        if optional not in df.columns:
            df[optional] = ""
    return df

def read_uploaded_file(file):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Please upload a CSV or Excel file (.csv, .xlsx, .xls).")
    if suffix == ".csv":
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    return ensure_columns(df)

@app.route("/")
def dashboard():
    with get_db() as conn:
        total = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        monthly_avg = conn.execute("""
            SELECT COALESCE(AVG(month_total),0) FROM (
                SELECT SUM(amount) AS month_total
                FROM expenses GROUP BY substr(date,1,7)
            )
        """).fetchone()[0]
        categories = conn.execute("""
            SELECT category, SUM(amount) AS total FROM expenses
            GROUP BY category ORDER BY total DESC
        """).fetchall()
        monthly_trend = conn.execute("""
            SELECT substr(date,1,7) AS month, SUM(amount) AS total
            FROM expenses GROUP BY month ORDER BY month
        """).fetchall()
        recent = conn.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC LIMIT 8").fetchall()
    return render_template("dashboard.html", total=total, count=count,
                           monthly=monthly_avg, categories=categories,
                           monthly_trend=monthly_trend, recent=recent)

@app.route("/transactions", methods=["GET", "POST"])
def transactions():
    message = ""
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Choose a CSV or Excel file first.", "error")
            return redirect(url_for("transactions"))
        try:
            df = read_uploaded_file(file)
            original_count = len(df)
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
            df["category"] = df["category"].fillna("").astype(str).str.strip()
            df["description"] = df["description"].fillna("").astype(str).str.strip()
            df["payment_method"] = df["payment_method"].fillna("").astype(str).str.strip()
            df = df.dropna(subset=["date", "amount"])
            df = df[df["category"] != ""]
            df = df[df["amount"] >= 0]
            df = df.drop_duplicates(subset=["date", "category", "description", "amount", "payment_method"])
            cleaned_count = len(df)
            with get_db() as conn:
                conn.executemany("""
                    INSERT INTO expenses (date, category, description, amount, payment_method)
                    VALUES (?, ?, ?, ?, ?)
                """, list(df[["date", "category", "description", "amount", "payment_method"]].itertuples(index=False, name=None)))
            flash(f"Imported {cleaned_count} records. {original_count - cleaned_count} invalid or duplicate rows were skipped.", "success")
        except Exception as exc:
            flash(f"Import failed: {exc}", "error")
        return redirect(url_for("transactions"))

    search = request.args.get("q", "").strip()
    with get_db() as conn:
        if search:
            rows = conn.execute("""
                SELECT * FROM expenses
                WHERE category LIKE ? OR description LIKE ? OR payment_method LIKE ?
                ORDER BY date DESC, id DESC
            """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
        else:
            rows = conn.execute("SELECT * FROM expenses ORDER BY date DESC, id DESC").fetchall()
    return render_template("transactions.html", rows=rows, search=search)

@app.route("/transactions/add", methods=["POST"])
def add_transaction():
    date = request.form.get("date", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    payment_method = request.form.get("payment_method", "").strip()
    try:
        amount = float(request.form.get("amount", ""))
        parsed_date = pd.to_datetime(date, errors="raise").strftime("%Y-%m-%d")
        if amount < 0 or not category:
            raise ValueError("Amount must be non-negative and category is required.")
        with get_db() as conn:
            conn.execute("""
                INSERT INTO expenses (date, category, description, amount, payment_method)
                VALUES (?, ?, ?, ?, ?)
            """, (parsed_date, category, description, amount, payment_method))
        flash("Expense added successfully.", "success")
    except Exception as exc:
        flash(f"Could not add expense: {exc}", "error")
    return redirect(url_for("transactions"))

@app.route("/transactions/delete/<int:expense_id>", methods=["POST"])
def delete_transaction(expense_id):
    with get_db() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    flash("Transaction deleted.", "success")
    return redirect(url_for("transactions"))

@app.route("/analysis")
def analysis():
    return render_template("analysis.html")

@app.route("/api/amounts")
def api_amounts():
    with get_db() as conn:
        rows = conn.execute("SELECT amount FROM expenses ORDER BY id").fetchall()
    return jsonify({"amounts": [row["amount"] for row in rows]})


@app.route("/api/analysis")
def api_analysis():
    with get_db() as conn:
        amounts = conn.execute("SELECT amount FROM expenses ORDER BY id").fetchall()
        categories = conn.execute("""
            SELECT category, SUM(amount) AS total FROM expenses
            GROUP BY category ORDER BY total DESC
        """).fetchall()
    return jsonify({
        "amounts": [row["amount"] for row in amounts],
        "categories": [row["category"] for row in categories],
        "category_totals": [row["total"] for row in categories]
    })

@app.route("/trends")
def trends():
    with get_db() as conn:
        df = pd.read_sql_query("SELECT date, amount FROM expenses ORDER BY date", conn)
    months, totals, averages, forecast, future_months = [], [], [], [], []
    message = "Add expense records to see your monthly trends."
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        if not df.empty:
            df["month"] = df["date"].dt.to_period("M")
            monthly = df.groupby("month")["amount"].sum().sort_index()
            months = monthly.index.astype(str).tolist()
            totals = [float(x) for x in monthly.tolist()]
            averages = [None if pd.isna(x) else float(x) for x in monthly.rolling(3).mean().tolist()]
            message = "Monthly totals and a 3-month moving average are shown below."
            if len(monthly) >= 12:
                try:
                    from statsmodels.tsa.arima.model import ARIMA
                    fitted = ARIMA(monthly.astype(float), order=(1, 1, 1)).fit()
                    forecast = [max(0, float(x)) for x in fitted.forecast(steps=3).tolist()]
                    last = monthly.index[-1]
                    future_months = [str(last + i) for i in (1, 2, 3)]
                    message = "Forecast is an estimate based on your historical data, not a guarantee."
                except Exception:
                    message = "Trend is available; forecasting could not be calculated for this dataset."
            else:
                message += " Add at least 12 distinct months of data to enable the demo ARIMA forecast."
    return render_template("trends.html", months=months, totals=totals,
                           averages=averages, forecast=forecast,
                           future_months=future_months, message=message)

@app.route("/reports")
def reports():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT substr(date,1,7) AS month, category, SUM(amount) AS total
            FROM expenses GROUP BY month, category ORDER BY month DESC, total DESC
        """).fetchall()
    return render_template("reports.html", rows=rows)

@app.route("/export.csv")
def export_csv():
    with get_db() as conn:
        df = pd.read_sql_query("SELECT date, category, description, amount, payment_method FROM expenses ORDER BY date", conn)
    from flask import Response
    return Response(df.to_csv(index=False), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=spendwise-expenses.csv"})

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
