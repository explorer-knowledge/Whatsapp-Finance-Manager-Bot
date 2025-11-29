import sqlite3
import os
from config import USER_DBS_DIR, MAX_CHAT_HISTORY

def init_user_db(phone):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS expense (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_taken TEXT NOT NULL,
        amount REAL NOT NULL,
        source TEXT,
        interest_rate REAL,
        emi_amount REAL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

def add_to_chat_history(phone, role, message):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (role, message) VALUES (?, ?)", (role, message))
    c.execute(f"DELETE FROM chat_history WHERE id NOT IN (SELECT id FROM chat_history ORDER BY id DESC LIMIT {MAX_CHAT_HISTORY})")
    conn.commit()
    conn.close()

def get_chat_history(phone, limit=None):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    limit_clause = f"LIMIT {limit}" if limit else f"LIMIT {MAX_CHAT_HISTORY}"
    c.execute(f"SELECT role, message FROM chat_history ORDER BY id DESC {limit_clause}")
    history = c.fetchall()
    conn.close()
    return list(reversed(history))

def add_income_db(phone, date, amount, category, description):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO income (date, amount, category, description) VALUES (?, ?, ?, ?)",
              (date, amount, category, description))
    transaction_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"status":"success","transaction_id": transaction_id}

def add_expense_db(phone, date, amount, category, description):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO expense (date, amount, category, description) VALUES (?, ?, ?, ?)",
              (date, amount, category, description))
    transaction_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"status":"success","transaction_id": transaction_id}

def update_transaction_db(phone, transaction_type, transaction_id, field, new_value):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    table = transaction_type.lower()
    if table not in ['income','expense']:
        conn.close()
        return {"status":"error","message":"Invalid transaction type"}
    allowed_fields = ['date','amount','category','description']
    if field not in allowed_fields:
        conn.close()
        return {"status":"error","message":"Invalid field"}
    c.execute(f"SELECT * FROM {table} WHERE id = ?", (transaction_id,))
    if not c.fetchone():
        conn.close()
        return {"status":"error","message":"Transaction not found"}
    c.execute(f"UPDATE {table} SET {field} = ? WHERE id = ?", (new_value, transaction_id))
    conn.commit()
    conn.close()
    return {"status":"success","message":"Updated"}

def delete_transaction_db(phone, transaction_type, transaction_id):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    table = transaction_type.lower()
    if table not in ['income','expense']:
        conn.close()
        return {"status":"error","message":"Invalid transaction type"}
    c.execute(f"DELETE FROM {table} WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    return {"status":"success","message":"Deleted"}

def view_transactions_db(phone, transaction_type=None, start_date=None, end_date=None, limit=None):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    results = {"income": [], "expense": []}
    types = [transaction_type] if transaction_type else ['income','expense']
    for ttype in types:
        query = f"SELECT * FROM {ttype}"
        params = []
        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            query += " WHERE date >= ?"
            params = [start_date]
        elif end_date:
            query += " WHERE date <= ?"
            params = [end_date]
        query += " ORDER BY date DESC, id DESC"
        if limit:
            query += f" LIMIT {limit}"
        c.execute(query, params)
        rows = c.fetchall()
        results[ttype] = [{"id": r[0], "date": r[1], "amount": r[2], "category": r[3], "description": r[4]} for r in rows]
    conn.close()
    return results

def add_loan_db(phone, amount, source, date_taken, interest_rate, emi_amount):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO loans (date_taken, amount, source, interest_rate, emi_amount) VALUES (?, ?, ?, ?, ?)",
              (date_taken, amount, source, interest_rate, emi_amount))
    loan_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"status":"success","loan_id": loan_id}

def get_active_loans_db(phone):
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("SELECT amount, source, interest_rate, emi_amount FROM loans WHERE status='active'")
        rows = c.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return rows

def calculate_loan_interest(phone, amount, interest_rate, tenure_years=1):
    try:
        interest = (amount * interest_rate * tenure_years) / 100
        total_amount = amount + interest
        return {"status":"success","interest_amount": interest, "total_payable": total_amount}
    except Exception as e:
        return {"status":"error","message": str(e)}
