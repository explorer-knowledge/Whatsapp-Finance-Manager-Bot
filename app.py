import os
import sqlite3
import json
import secrets
import requests
import base64
from datetime import datetime, timedelta
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import re

app = Flask(__name__)

# ===========================
# CONFIGURATION
# ===========================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Changed model from gemini-2.5-flash to gemini-1.5-flash for better stability
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
)

# Chat history configuration
MAX_CHAT_HISTORY = int(os.environ.get("MAX_CHAT_HISTORY", "50"))

# Database directories
USER_DBS_DIR = "user_dbs"
os.makedirs(USER_DBS_DIR, exist_ok=True)

# Debug/Logging configuration
ENABLE_DETAILED_LOGGING = True  # Set to False to disable terminal output

# ===========================
# LOGGING FUNCTIONS (Can be disabled)
# ===========================

def log_separator():
    """Print separator line"""
    if ENABLE_DETAILED_LOGGING:
        print("\n" + "=" * 80)

def log_section(title):
    """Print section header"""
    if ENABLE_DETAILED_LOGGING:
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

def log_info(label, content, indent=0):
    """Print labeled information"""
    if ENABLE_DETAILED_LOGGING:
        prefix = "  " * indent
        print(f"{prefix}[{label}]: {content}")

def log_json(label, data, indent=0):
    """Print JSON data in formatted way"""
    if ENABLE_DETAILED_LOGGING:
        prefix = "  " * indent
        print(f"{prefix}[{label}]:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

def log_user_input(phone, message):
    """Log incoming user message"""
    if ENABLE_DETAILED_LOGGING:
        log_section(f"📱 INCOMING MESSAGE FROM {phone}")
        log_info("User Message", message, 1)
        log_info("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1)

def log_ai_request(prompt):
    """Log AI request"""
    if ENABLE_DETAILED_LOGGING:
        log_section("🤖 AI REQUEST")
        log_info("Input", "Text Only", 1)
        log_info("Prompt Length", f"{len(prompt)} characters", 1)
        print("\n--- PROMPT START ---")
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print("--- PROMPT END ---\n")

def log_ai_response(response):
    """Log AI raw response"""
    if ENABLE_DETAILED_LOGGING:
        log_section("🧠 AI RAW RESPONSE")
        print(response)

def log_parsed_actions(actions_json):
    """Log parsed AI actions"""
    if ENABLE_DETAILED_LOGGING:
        log_section("⚙️ PARSED ACTIONS")
        log_json("Actions JSON", actions_json, 1)

def log_function_execution(function_name, params, result):
    """Log function execution"""
    if ENABLE_DETAILED_LOGGING:
        print(f"\n  🔧 EXECUTING: {function_name}")
        log_json("Parameters", params, 2)
        log_json("Result", result, 2)

def log_final_response(response_text):
    """Log final bot response"""
    if ENABLE_DETAILED_LOGGING:
        log_section("💬 BOT RESPONSE")
        print(response_text)
        log_separator()

def log_error(error_message, exception=None):
    """Log errors"""
    if ENABLE_DETAILED_LOGGING:
        log_section("❌ ERROR")
        log_info("Error", error_message, 1)
        if exception:
            log_info("Exception", str(exception), 1)

# ===========================
# DATABASE FUNCTIONS
# ===========================

def init_users_db():
    """Initialize the main users database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY,
        name TEXT DEFAULT 'User',
        privacy_accepted TEXT DEFAULT 'no',
        unique_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def init_user_db(phone):
    """Initialize individual user database with income, expense, chat, and LOANS tables"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Income table
    c.execute('''CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Expense table
    c.execute('''CREATE TABLE IF NOT EXISTS expense (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # --- NEW: Loan Table ---
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
    
    # Chat history table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

def check_user_exists(phone):
    """Check if user exists in users.db"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = c.fetchone()
    conn.close()
    return user

def create_new_user(phone):
    """Create new user with unique ID"""
    unique_id = secrets.token_hex(10)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (phone, unique_id, privacy_accepted) VALUES (?, ?, 'no')", 
              (phone, unique_id))
    conn.commit()
    conn.close()
    init_user_db(phone)
    return unique_id

def update_privacy_acceptance(phone, accepted):
    """Update privacy policy acceptance"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET privacy_accepted = ? WHERE phone = ?", (accepted, phone))
    conn.commit()
    conn.close()

def get_privacy_status(phone):
    """Get privacy acceptance status"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT privacy_accepted FROM users WHERE phone = ?", (phone,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def add_to_chat_history(phone, role, message):
    """Add message to chat history, maintain max MAX_CHAT_HISTORY messages"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("INSERT INTO chat_history (role, message) VALUES (?, ?)", (role, message))
    c.execute(f"DELETE FROM chat_history WHERE id NOT IN (SELECT id FROM chat_history ORDER BY id DESC LIMIT {MAX_CHAT_HISTORY})")
    
    conn.commit()
    conn.close()

def get_chat_history(phone, limit=None):
    """Get chat history for context"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    limit_clause = f"LIMIT {limit}" if limit else f"LIMIT {MAX_CHAT_HISTORY}"
    c.execute(f"SELECT role, message FROM chat_history ORDER BY id DESC {limit_clause}")
    history = c.fetchall()
    conn.close()
    return list(reversed(history))

def get_user_name(phone):
    """Get user's name"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT name FROM users WHERE phone = ?", (phone,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "User"

# ===========================
# CATEGORY DETERMINATION
# ===========================

CATEGORY_KEYWORDS = {
    "Food & Beverage": [
        "chai", "coffee", "tea", "food", "khana", "breakfast", "lunch", "dinner",
        "restaurant", "cafe", "pizza", "burger", "biryani", "snack", "nashta",
        "sweets", "mithai", "juice", "drink", "meal", "dine", "eat", "khaana"
    ],
    "Shopping": [
        "shopping", "shop", "clothes", "shirt", "pant", "shoes", "dress", "mall",
        "online", "amazon", "flipkart", "myntra", "purchase", "buy", "bought",
        "kapde", "jeans", "kurti", "saree"
    ],
    "Entertainment": [
        "party", "movie", "film", "concert", "game", "gaming", "netflix", "prime",
        "subscription", "entertainment", "fun", "outing", "picnic", "trip",
        "vacation", "holiday", "ghoomna", "masti"
    ],
    "Transport": [
        "uber", "ola", "taxi", "cab", "auto", "rickshaw", "petrol", "diesel",
        "fuel", "bus", "train", "metro", "flight", "travel", "parking",
        "toll", "vehicle", "gaadi", "bike", "car"
    ],
    "Bills & Utilities": [
        "electricity", "bill", "internet", "wifi", "phone", "mobile", "recharge",
        "water", "gas", "cylinder", "rent", "maintenance", "utility",
        "broadband", "postpaid", "prepaid"
    ],
    "Health & Fitness": [
        "medicine", "medical", "doctor", "hospital", "clinic", "pharmacy",
        "chemist", "health", "gym", "fitness", "yoga", "exercise", "dawai",
        "treatment", "checkup", "test", "lab"
    ],
    "Education": [
        "book", "books", "course", "class", "tuition", "school", "college",
        "university", "fees", "education", "learning", "study", "coaching",
        "tutorial", "exam", "kitab", "padhai"
    ],
    "Groceries": [
        "grocery", "groceries", "vegetables", "sabzi", "fruits", "milk",
        "ration", "kirana", "supermarket", "dmart", "bigbasket", "provisions"
    ],
    "Personal Care": [
        "salon", "haircut", "shaving", "parlour", "spa", "beauty", "cosmetics",
        "makeup", "grooming", "personal"
    ],
    "Investment": [
        "investment", "stock", "mutual fund", "sip", "fd", "deposit", "gold",
        "bitcoin", "crypto", "invest", "savings"
    ],
    "EMI & Loans": [
        "emi", "loan", "credit", "debt", "installment", "payment", "card"
    ],
    "Gifts & Donations": [
        "gift", "donation", "charity", "contribute", "help", "support", "present",
        "tohfa", "daan"
    ],
    "Salary": [
        "salary", "income", "earning", "wages", "payment received", "credit",
        "tankhwah", "kamai"
    ],
    "Freelance": [
        "freelance", "project", "client", "work", "gig", "contract"
    ],
    "Business": [
        "business", "profit", "sale", "revenue", "customer", "vyapar"
    ]
}

def determine_category_from_text(text, transaction_type="expense"):
    """Intelligently determine category based on keywords in text"""
    text_lower = text.lower()
    category_scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text_lower:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                    score += 2
                else:
                    score += 1
        
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1])[0]
        
        if transaction_type == "income":
            income_categories = ["Salary", "Freelance", "Business", "Investment"]
            if best_category in income_categories:
                return best_category
            else:
                return "Other Income"
        else:
            return best_category
    
    return "Other Income" if transaction_type == "income" else "Other"

# ===========================
# AI FUNCTION DEFINITIONS
# ===========================

def request_data_deletion(phone):
    """Return instructions for data deletion request"""
    contact_email = "support@example.com"
    contact_number = "+1-234-567-890"

    message = (f"Please contact these contacts; your data will be deleted from here:\n\n"
               f"📧 Email: {contact_email}\n"
               f"📞 Phone: {contact_number}")
    
    result = {
        "status": "success",
        "deletion_message": message
    }
    
    log_function_execution("request_data_deletion", {"phone": phone}, result)
    return result

# --- NEW FEATURES START ---

def predict_recurring_expenses_db(phone):
    """Analyze history to predict upcoming recurring expenses"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Get last 60 days of expenses
    sixty_days_ago = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    c.execute("SELECT date, amount, category, description FROM expense WHERE date >= ? ORDER BY date ASC", (sixty_days_ago,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return {"status": "success", "message": "Not enough data to predict expenses."}

    # Simple logic: Detect descriptions/categories that appear multiple times
    frequency = {}
    for r in rows:
        key = (r[2], r[3]) # Category, Description
        if key not in frequency:
            frequency[key] = []
        frequency[key].append(r)

    predictions = []
    
    for (cat, desc), transactions in frequency.items():
        if len(transactions) >= 2:
            # Calculate average amount
            avg_amt = sum(t[1] for t in transactions) / len(transactions)
            # Estimate next date (based on last transaction day)
            last_date_obj = datetime.strptime(transactions[-1][0], "%Y-%m-%d")
            
            # If the last transaction was last month, expect it this month
            next_due_date = last_date_obj + timedelta(days=30)
            days_until = (next_due_date - datetime.now()).days
            
            if days_until > -5: # Only show if it's upcoming or slightly overdue
                predictions.append(f"• {desc} ({cat}): ~Rs{avg_amt:.0f} expected around {next_due_date.strftime('%d %b')}")

    if not predictions:
        return {"status": "success", "message": "No obvious recurring expenses found yet."}

    report = "🔮 *Upcoming Expense Predictions:*\nBased on your history, keep funds ready for:\n" + "\n".join(predictions)
    
    log_function_execution("predict_recurring_expenses_db", {"phone": phone}, {"count": len(predictions)})
    return {"status": "success", "prediction_report": report}

# --- NEW FEATURES END ---

def add_income_db(phone, date, amount, category, description):
    """Add income entry to database"""
    if not category or category == "Other":
        category = determine_category_from_text(description, "income")
    
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO income (date, amount, category, description) VALUES (?, ?, ?, ?)",
              (date, amount, category, description))
    transaction_id = c.lastrowid
    conn.commit()
    conn.close()
    
    result = {
        "status": "success",
        "message": f"Income of ₹{amount} added for {date}",
        "transaction_id": transaction_id,
        "category": category
    }
    
    log_function_execution("add_income_db", {
        "phone": phone, "date": date, "amount": amount, "category": category, "description": description
    }, result)
    
    return result

def add_expense_db(phone, date, amount, category, description):
    """Add expense entry to database"""
    if not category or category == "Other":
        category = determine_category_from_text(description, "expense")
    
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO expense (date, amount, category, description) VALUES (?, ?, ?, ?)",
              (date, amount, category, description))
    transaction_id = c.lastrowid
    conn.commit()
    conn.close()
    
    result = {
        "status": "success",
        "message": f"Expense of ₹{amount} added for {date}",
        "transaction_id": transaction_id,
        "category": category
    }
    
    log_function_execution("add_expense_db", {
        "phone": phone, "date": date, "amount": amount, "category": category, "description": description
    }, result)
    
    return result

# --- NEW LOAN FUNCTIONS START ---

def add_loan_db(phone, amount, source, date_taken, interest_rate, emi_amount):
    """Add a new loan to the database"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO loans (date_taken, amount, source, interest_rate, emi_amount) VALUES (?, ?, ?, ?, ?)",
              (date_taken, amount, source, interest_rate, emi_amount))
    loan_id = c.lastrowid
    conn.commit()
    conn.close()

    result = {
        "status": "success",
        "message": f"Loan of ₹{amount} recorded.",
        "loan_id": loan_id
    }
    log_function_execution("add_loan_db", {
        "phone": phone, "amount": amount, "source": source, "date": date_taken
    }, result)
    return result

def calculate_loan_interest(phone, amount, interest_rate, tenure_years=1):
    """Calculate total interest payable on a loan"""
    try:
        interest = (amount * interest_rate * tenure_years) / 100
        total_amount = amount + interest
        message = (f"Interest Calculation:\n"
                   f"Principal: Rs{amount}\n"
                   f"Rate: {interest_rate}%\n"
                   f"Time: {tenure_years} years\n"
                   f"Total Interest: Rs{interest:.2f}\n"
                   f"Total Payable: Rs{total_amount:.2f}")
        
        result = {
            "status": "success",
            "interest_analysis": message,
            "interest_amount": interest,
            "total_payable": total_amount
        }
    except Exception as e:
        result = {"status": "error", "message": f"Calculation failed: {str(e)}"}
        
    log_function_execution("calculate_loan_interest", {
        "phone": phone, "amount": amount, "rate": interest_rate, "years": tenure_years
    }, result)
    return result

def get_active_loans_db(phone):
    """Get active loans for context"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Ensure table exists before querying (Just in case, though init_user_db handles it)
    try:
        c.execute("SELECT amount, source, interest_rate, emi_amount FROM loans WHERE status='active'")
        rows = c.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    
    loans = []
    for r in rows:
        loans.append(f"Amount: Rs{r[0]}, Source: {r[1]}, Interest: {r[2]}%, EMI: Rs{r[3]}")
    return loans

# --- NEW LOAN FUNCTIONS END ---

def update_transaction_db(phone, transaction_type, transaction_id, field, new_value):
    """Update a transaction field"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    allowed_fields = ['date', 'amount', 'category', 'description']
    if field not in allowed_fields:
        conn.close()
        result = {"status": "error", "message": f"Invalid field. Allowed: {', '.join(allowed_fields)}"}
        log_function_execution("update_transaction_db", {
            "phone": phone, "transaction_type": transaction_type, "transaction_id": transaction_id,
            "field": field, "new_value": new_value
        }, result)
        return result
    
    table = transaction_type.lower()
    if table not in ['income', 'expense']:
        conn.close()
        result = {"status": "error", "message": "Invalid transaction type"}
        log_function_execution("update_transaction_db", {
            "phone": phone, "transaction_type": transaction_type, "transaction_id": transaction_id,
            "field": field, "new_value": new_value
        }, result)
        return result
    
    c.execute(f"SELECT * FROM {table} WHERE id = ?", (transaction_id,))
    if not c.fetchone():
        conn.close()
        result = {"status": "error", "message": f"Transaction ID {transaction_id} not found"}
        log_function_execution("update_transaction_db", {
            "phone": phone, "transaction_type": transaction_type, "transaction_id": transaction_id,
            "field": field, "new_value": new_value
        }, result)
        return result
    
    c.execute(f"UPDATE {table} SET {field} = ? WHERE id = ?", (new_value, transaction_id))
    conn.commit()
    conn.close()
    
    result = {
        "status": "success",
        "message": f"Updated {field} to '{new_value}' for transaction ID {transaction_id}"
    }
    
    log_function_execution("update_transaction_db", {
        "phone": phone, "transaction_type": transaction_type, "transaction_id": transaction_id,
        "field": field, "new_value": new_value
    }, result)
    
    return result

def delete_transaction_db(phone, transaction_type, transaction_id):
    """Delete a transaction"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    table = transaction_type.lower()
    if table not in ['income', 'expense']:
        conn.close()
        result = {"status": "error", "message": "Invalid transaction type"}
        log_function_execution("delete_transaction_db", {
            "phone": phone, "transaction_type": transaction_type, "transaction_id": transaction_id
        }, result)
        return result
    
    c.execute(f"DELETE FROM {table} WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    
    result = {
        "status": "success",
        "message": f"Deleted {transaction_type} transaction ID {transaction_id}"
    }
    
    log_function_execution("delete_transaction_db", {
        "phone": phone, "transaction_type": transaction_type, "transaction_id": transaction_id
    }, result)
    
    return result

def update_user_name_db(phone, new_name):
    """Update user's name"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET name = ? WHERE phone = ?", (new_name, phone))
    conn.commit()
    conn.close()
    
    result = {"status": "success", "message": f"Name updated to {new_name}"}
    log_function_execution("update_user_name_db", {"phone": phone, "new_name": new_name}, result)
    
    return result

def view_transactions_db(phone, transaction_type=None, start_date=None, end_date=None, limit=None):
    """View transactions with optional filters"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    results = {"income": [], "expense": []}
    
    types = [transaction_type] if transaction_type else ['income', 'expense']
    
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
    
    log_function_execution("view_transactions_db", {
        "phone": phone, "transaction_type": transaction_type,
        "start_date": start_date, "end_date": end_date, "limit": limit
    }, {"results_count": sum(len(v) for v in results.values())})
    
    return results

def get_summary_db(phone, start_date=None, end_date=None):
    """Get financial summary"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    query = "SELECT SUM(amount), COUNT(*) FROM income"
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
    
    c.execute(query, params)
    income_result = c.fetchone()
    total_income = income_result[0] or 0
    income_count = income_result[1] or 0
    
    query = "SELECT SUM(amount), COUNT(*) FROM expense"
    if params:
        if len(params) == 2:
            query += " WHERE date BETWEEN ? AND ?"
        elif start_date:
            query += " WHERE date >= ?"
        else:
            query += " WHERE date <= ?"
    c.execute(query, params)
    expense_result = c.fetchone()
    total_expense = expense_result[0] or 0
    expense_count = expense_result[1] or 0
    
    query = "SELECT category, SUM(amount), COUNT(*) FROM expense"
    if params:
        if len(params) == 2:
            query += " WHERE date BETWEEN ? AND ?"
        elif start_date:
            query += " WHERE date >= ?"
        else:
            query += " WHERE date <= ?"
    query += " GROUP BY category ORDER BY SUM(amount) DESC"
    c.execute(query, params)
    category_expenses = {row[0]: {"amount": row[1], "count": row[2]} for row in c.fetchall()}
    
    query = "SELECT category, SUM(amount), COUNT(*) FROM income"
    if params:
        if len(params) == 2:
            query += " WHERE date BETWEEN ? AND ?"
        elif start_date:
            query += " WHERE date >= ?"
        else:
            query += " WHERE date <= ?"
    query += " GROUP BY category ORDER BY SUM(amount) DESC"
    c.execute(query, params)
    category_income = {row[0]: {"amount": row[1], "count": row[2]} for row in c.fetchall()}
    
    conn.close()
    
    balance = total_income - total_expense
    result = {
        "total_income": total_income,
        "income_count": income_count,
        "total_expense": total_expense,
        "expense_count": expense_count,
        "balance": balance,
        "category_expenses": category_expenses,
        "category_income": category_income,
        "period": f"{start_date or 'beginning'} to {end_date or 'now'}"
    }
    
    log_function_execution("get_summary_db", {
        "phone": phone, "start_date": start_date, "end_date": end_date
    }, {"balance": balance, "total_transactions": income_count + expense_count})
    
    return result

# --- NEW HELPER FOR PLANNING ---

def get_financial_health_snapshot(phone):
    """Get a snapshot for AI to generate advice"""
    # Get current month summary
    today = datetime.now()
    start_date = today.replace(day=1).strftime("%Y-%m-%d")
    summary = get_summary_db(phone, start_date=start_date)
    
    # Get Loans
    active_loans = get_active_loans_db(phone)
    loans_text = "\n".join(active_loans) if active_loans else "No active loans detected."

    return (f"FINANCIAL SNAPSHOT (Current Month):\n"
            f"- Total Income: Rs{summary['total_income']}\n"
            f"- Total Expenses: Rs{summary['total_expense']}\n"
            f"- Current Balance: Rs{summary['balance']}\n"
            f"- Top Expense Categories: {', '.join(list(summary['category_expenses'].keys())[:3])}\n"
            f"ACTIVE LOANS:\n{loans_text}")

def get_last_transaction_db(phone, transaction_type=None, limit=5):
    """Get last N transactions for context"""
    db_path = os.path.join(USER_DBS_DIR, f"{phone}.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    results = []
    
    types = [transaction_type] if transaction_type else ['income', 'expense']
    
    for ttype in types:
        c.execute(f"SELECT * FROM {ttype} ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        for r in rows:
            results.append({
                "id": r[0],
                "type": ttype,
                "date": r[1],
                "amount": r[2],
                "category": r[3],
                "description": r[4]
            })
    
    conn.close()
    
    results.sort(key=lambda x: x['id'], reverse=True)
    
    return results[:limit]

# ===========================
# AI SYSTEM PROMPT
# ===========================

def get_system_prompt(current_date, yesterday, tomorrow, phone):
    """Generate comprehensive system prompt with context"""
    
    recent_transactions = get_last_transaction_db(phone, limit=10)
    transactions_context = "\n".join([
        f"  ID {t['id']} ({t['type']}): {t['date']} - Rs{t['amount']} - {t['category']} - {t['description']}"
        for t in recent_transactions
    ]) if recent_transactions else "  No transactions yet"
    
    # NEW: Get snapshot for Planning features
    financial_snapshot = get_financial_health_snapshot(phone)
    
    return """You are an intelligent WhatsApp Finance Manager Bot & Expert Financial Advisor. 
Interpret natural language and execute database operations.

CURRENT DATE: """ + current_date + """
YESTERDAY: """ + yesterday + """
TOMORROW: """ + tomorrow + """

""" + financial_snapshot + """

RECENT TRANSACTIONS:
""" + transactions_context + """

FUNCTIONS AVAILABLE:
1. add_income_db(phone, date, amount, category, description)
2. add_expense_db(phone, date, amount, category, description)
3. update_transaction_db(phone, transaction_type, transaction_id, field, new_value)
4. delete_transaction_db(phone, transaction_type, transaction_id)
5. update_user_name_db(phone, new_name)
6. view_transactions_db(phone, transaction_type, start_date, end_date, limit)
7. get_summary_db(phone, start_date, end_date)
8. request_data_deletion(phone) - Use ONLY when user explicitly asks to delete their account, profile, or all data.
9. predict_recurring_expenses_db(phone) - Use this when user asks about "upcoming expenses", "what bills are due", or needs future planning advice.
10. add_loan_db(phone, amount, source, date_taken, interest_rate, emi_amount)
11. calculate_loan_interest(phone, amount, interest_rate, tenure_years)

DATE PARSING: today/aaj=""" + current_date + """, yesterday/kal=""" + yesterday + """, tomorrow=""" + tomorrow + """

RESPOND IN JSON:
{
  "actions": [
    {
      "function": "function_name",
      "params": {"param1": "value1"}
    }
  ],
  "response_text": "Friendly message"
}

*** CRITICAL: CALCULATION VERIFICATION PROTOCOL ***
- **Self-Correction:** Before outputting any number, verify the calculation.
- **Interest Calculation:** When a user adds a loan, you MUST calculate the Total Interest Payable based on the rate.
  - Formula: Total Interest = (Principal * Interest Rate * Time in Years) / 100.
  - Tell the user specifically: "Total interest you will pay is Rs [Amount]."
- **Accuracy Check:** If you are estimating an EMI or Total Repayment, ensure you apply the mathematical formulas correctly. Do not guess; calculate.
- **Double Check:** Review your 'response_text' for any arithmetic errors before finalizing the JSON.

ADVISOR GUIDELINES:
- **Budget Plans:** If user asks for a budget, analyze their 'Financial Snapshot'. Suggest a 50/30/20 rule (50% needs, 30% wants, 20% savings) based on their INCOME.
- **Loan/Repayment Plans:** If user asks for a loan plan, look at their 'Current Balance' and 'ACTIVE LOANS'. Suggest an EMI they can afford.
- **Expert Advice:** If user asks for advice, interpret their top expense categories.

RULES:
- Extract amounts (handle 5k=5000, 1.5 lakh=150000)
- Leave category as "Other" for auto-detection
- Generate concise descriptions
- Execute multiple actions if needed
- Use transaction IDs from context for edits
- Always respond in valid JSON

LOAN LOGIC:
- If a user mentions taking a loan (e.g., "I took a 5 lakh loan"), you MUST collect the following before saving:
  1. Date Taken
  2. Interest Rate (%)
  3. EMI Amount
  4. Source (Bank name or Person)
- IF details are missing, your response_text should be a question asking for them (Do NOT call the function yet).
- ONLY call `add_loan_db` when you have ALL parameters.
- After saving a loan, provide advice on how to manage it based on their income.
"""

# ===========================
# AI INTERACTION
# ===========================

def call_gemini_api(prompt):
    """Call Gemini API with REST endpoint (Text Only)"""
    try:
        headers = {"Content-Type": "application/json"}
        
        parts = [{"text": prompt}]
        
        data = {
            "contents": [{
                "parts": parts
            }],
            "generationConfig": {
                "temperature": 0.4,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 4096,
            }
        }
        
        log_ai_request(prompt)
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        if 'candidates' in result and len(result['candidates']) > 0:
            text = result['candidates'][0]['content']['parts'][0]['text']
            log_ai_response(text)
            return text
        else:
            log_error("No candidates in Gemini response", result)
            return None
            
    except requests.exceptions.Timeout:
        log_error("Gemini API timeout")
        return None
    except requests.exceptions.RequestException as e:
        log_error("Gemini API request failed", e)
        return None
    except Exception as e:
        log_error("Unexpected error in Gemini API call", e)
        return None

def parse_date_from_text(date_text, current_date):
    """Parse various date formats"""
    date_text_lower = date_text.lower().strip()
    
    current_dt = datetime.strptime(current_date, "%Y-%m-%d")
    
    if date_text_lower in ['today', 'aaj']:
        return current_date
    
    if date_text_lower in ['yesterday', 'kal']:
        return (current_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if date_text_lower in ['tomorrow']:
        return (current_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if date_text_lower in ['parso']:
        return (current_dt - timedelta(days=2)).strftime("%Y-%m-%d")
    
    days_ago_match = re.search(r'(\d+)\s*days?\s*ago', date_text_lower)
    if days_ago_match:
        days = int(days_ago_match.group(1))
        return (current_dt - timedelta(days=days)).strftime("%Y-%m-%d")
    
    try:
        parsed = datetime.strptime(date_text, "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d")
    except:
        pass
    
    try:
        parsed = datetime.strptime(date_text, "%d/%m/%Y")
        return parsed.strftime("%Y-%m-%d")
    except:
        pass
    
    return current_date

def execute_ai_actions(phone, actions_json):
    """Execute actions from AI response"""
    results = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    for action in actions_json.get("actions", []):
        function_name = action.get("function")
        params = action.get("params", {})
        
        params["phone"] = phone
        
        if "date" in params:
            params["date"] = parse_date_from_text(params["date"], current_date)
        
        if "amount" in params:
            try:
                amount_str = str(params["amount"]).lower().replace(',', '')
                if 'k' in amount_str:
                    amount_str = amount_str.replace('k', '')
                    params["amount"] = float(amount_str) * 1000
                elif 'lakh' in amount_str:
                    amount_str = amount_str.replace('lakh', '').strip()
                    params["amount"] = float(amount_str) * 100000
                else:
                    params["amount"] = float(amount_str)
            except ValueError:
                params["amount"] = 0
        
        try:
            if function_name == "add_income_db":
                result = add_income_db(**params)
            elif function_name == "add_expense_db":
                result = add_expense_db(**params)
            elif function_name == "update_transaction_db":
                result = update_transaction_db(**params)
            elif function_name == "delete_transaction_db":
                result = delete_transaction_db(**params)
            elif function_name == "update_user_name_db":
                result = update_user_name_db(**params)
            elif function_name == "view_transactions_db":
                result = view_transactions_db(**params)
            elif function_name == "get_summary_db":
                result = get_summary_db(**params)
            elif function_name == "request_data_deletion":
                result = request_data_deletion(**params)
            # NEW: Planning & Prediction
            elif function_name == "predict_recurring_expenses_db":
                result = predict_recurring_expenses_db(**params)
            # NEW: Loan management
            elif function_name == "add_loan_db":
                result = add_loan_db(**params)
            # NEW: Interest Calculation
            elif function_name == "calculate_loan_interest":
                result = calculate_loan_interest(**params)
            else:
                result = {"status": "error", "message": f"Unknown function: {function_name}"}
            
            results.append(result)
        except TypeError as e:
            error_msg = f"Invalid parameters for {function_name}: {str(e)}"
            log_error(error_msg, e)
            results.append({"status": "error", "message": error_msg})
        except Exception as e:
            error_msg = f"Error executing {function_name}: {str(e)}"
            log_error(error_msg, e)
            results.append({"status": "error", "message": error_msg})
    
    return results

def format_transaction_results(results):
    """Format transaction results for display"""
    formatted_text = ""
    
    for result in results:
        if isinstance(result, dict):
            # Handle Deletion Request Message
            if "deletion_message" in result:
                formatted_text += f"\n\n{result['deletion_message']}\n"

            # NEW: Handle Prediction Report
            if "prediction_report" in result:
                formatted_text += f"\n\n{result['prediction_report']}\n"
            
            # NEW: Handle Loan Addition
            if "loan_id" in result:
                formatted_text += f"\n\n✅ {result['message']} (ID: {result['loan_id']})\n"
            
            # NEW: Handle Interest Calculation
            if "interest_analysis" in result:
                 formatted_text += f"\n\n🧮 {result['interest_analysis']}\n"

            if "income" in result or "expense" in result:
                for trans_type in ["income", "expense"]:
                    transactions = result.get(trans_type, [])
                    if transactions:
                        formatted_text += f"\n\n*{trans_type.title()} Transactions:*\n"
                        for trans in transactions[:10]:
                            formatted_text += f"• ID {trans['id']}: {trans['date']} | Rs{trans['amount']:.2f}\n"
                            formatted_text += f"  {trans['category']} - {trans['description']}\n"
            
            elif "total_income" in result:
                formatted_text += f"\n\n📊 *Financial Summary*\n"
                formatted_text += f"Period: {result['period']}\n"
                formatted_text += f"{'─' * 40}\n"
                formatted_text += f"💰 Total Income: Rs{result['total_income']:,.2f} ({result['income_count']} transactions)\n"
                formatted_text += f"💸 Total Expense: Rs{result['total_expense']:,.2f} ({result['expense_count']} transactions)\n"
                formatted_text += f"{'─' * 40}\n"
                formatted_text += f"💵 Balance: Rs{result['balance']:,.2f}\n"
                
                if result.get('category_expenses'):
                    formatted_text += f"\n*Top Expense Categories:*\n"
                    for i, (cat, data) in enumerate(list(result['category_expenses'].items())[:5], 1):
                        formatted_text += f"{i}. {cat}: Rs{data['amount']:,.2f} ({data['count']} transactions)\n"
                
                if result.get('category_income'):
                    formatted_text += f"\n*Income Sources:*\n"
                    for i, (cat, data) in enumerate(list(result['category_income'].items())[:5], 1):
                        formatted_text += f"{i}. {cat}: Rs{data['amount']:,.2f} ({data['count']} transactions)\n"
    
    return formatted_text

def get_ai_response(phone, user_message):
    """Get AI response using Gemini API (Text Only)"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    history = get_chat_history(phone, limit=20)
    context = "\n".join([f"{role}: {msg}" for role, msg in history[-10:]])
    
    user_name = get_user_name(phone)
    
    system_prompt = get_system_prompt(current_date, yesterday, tomorrow, phone)
    
    full_prompt = system_prompt + """

USER INFO:
- Phone: """ + phone + """
- Name: """ + user_name + """

RECENT CHAT:
""" + (context if context else "No previous conversation") + """

USER MESSAGE: """ + user_message + """

Analyze and respond in JSON format with actions and response_text."""
    
    ai_response = call_gemini_api(full_prompt)
    
    if not ai_response:
        log_error("No response from Gemini API")
        return "Sorry, I'm having trouble connecting right now. Please try again."
    
    try:
        ai_response = ai_response.strip()
        
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:]
        elif ai_response.startswith("```"):
            ai_response = ai_response[3:]
        
        if ai_response.endswith("```"):
            ai_response = ai_response[:-3]
        
        ai_response = ai_response.strip()
        
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            ai_response = json_match.group(0)
        
        actions_json = json.loads(ai_response)
        log_parsed_actions(actions_json)
        
        results = execute_ai_actions(phone, actions_json)
        
        response_text = actions_json.get("response_text", "Done!")
        
        formatted_results = format_transaction_results(results)
        if formatted_results:
            response_text += formatted_results
        
        errors = [r.get("message") for r in results if isinstance(r, dict) and r.get("status") == "error"]
        if errors:
            response_text += "\n\n⚠️ *Some issues:*\n" + "\n".join(f"• {err}" for err in errors)
        
        # Ensure response does not exceed 1600 characters
        if len(response_text) > 1600:
            response_text = response_text[:1597] + "..."

        log_final_response(response_text)
        return response_text
        
    except json.JSONDecodeError as e:
        log_error("JSON parsing failed", e)
        log_info("Raw AI Response", ai_response)
        
        return ("I understood what you said, but I'm having trouble formatting my response. "
                "Could you try rephrasing that?")
    
    except Exception as e:
        log_error("Unexpected error in AI response processing", e)
        return "Oops! Something went wrong. Please try again."

# ===========================
# WHATSAPP WEBHOOK
# ===========================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '').replace('whatsapp:', '').replace('+', '')
    
    log_user_input(from_number, incoming_msg)
    
    resp = MessagingResponse()
    msg = resp.message()
    
    init_users_db()
    
    user = check_user_exists(from_number)
    
    if not user:
        create_new_user(from_number)
        log_info("New User", f"Created user {from_number}")
        
        privacy_msg = """🔐 *Welcome to Finance Manager Bot!*

Before we begin, please read our privacy policy:

📱 *We collect and store:*
• Your phone number
• Your name (optional)
• Transaction details you provide

🔒 *Privacy Commitment:*
• Your data is stored securely
• We do NOT share your information with any third party
• Data is used only to provide you finance management services

Do you accept our privacy policy?
Reply *YES* to continue or *NO* to decline."""
        
        msg.body(privacy_msg)
        log_final_response(privacy_msg)
        return str(resp)
    
    # Ensures database schema is up-to-date (creates 'loans' table if missing)
    init_user_db(from_number)

    privacy_status = get_privacy_status(from_number)
    
    if privacy_status == 'no':
        if incoming_msg.lower() in ['yes', 'y', 'हां', 'ha', 'haan', 'accept']:
            update_privacy_acceptance(from_number, 'yes')
            log_info("Privacy", f"User {from_number} accepted privacy policy")
            
            welcome_msg = """✅ *Thank you for accepting!*

Welcome to your personal Finance Manager! 🎉

*What I can do:*
💰 Track income: "Got salary 50000"
💸 Track expenses: "500 spent on chai"
📊 Get summaries: "Show this month summary"
🔮 Predict expenses: "What bills are coming up?"
📋 Get Plans: "Make a budget for me" or "Plan for loan repayment"
✏️ Edit anything: "Change last expense amount to 400"
🗑️ Delete entries: "Delete that chai expense"

Just message me naturally in Hindi or English!"""
            
            msg.body(welcome_msg)
            log_final_response(welcome_msg)
        else:
            decline_msg = "❌ *Privacy Policy Required*\n\nWe cannot provide our services without your consent.\n\nReply *YES* when ready to accept."
            msg.body(decline_msg)
            log_final_response(decline_msg)
        
        return str(resp)
    
    # Handle Chat History
    add_to_chat_history(from_number, 'user', incoming_msg)
    
    # Pass message only
    ai_response = get_ai_response(from_number, incoming_msg)
    
    add_to_chat_history(from_number, 'assistant', ai_response)
    
    msg.body(ai_response)
    return str(resp)

@app.route('/')
def home():
    """Home page with status"""
    status_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Finance Manager Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #25D366; }
            .status { 
                padding: 10px;
                background: #e8f5e9;
                border-left: 4px solid #4caf50;
                margin: 20px 0;
            }
            .config {
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                font-family: monospace;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 WhatsApp Finance Manager Bot</h1>
            <div class="status">
                <strong>Status:</strong> ✅ Active and Running
            </div>
            
            <h2>Configuration</h2>
            <div class="config">
                <p>✅ Database: Initialized</p>
                <p>""" + ('✅' if GEMINI_API_KEY else '❌') + """ Gemini API: """ + ('Configured' if GEMINI_API_KEY else 'NOT SET') + """</p>
                <p>📝 Max Chat History: """ + str(MAX_CHAT_HISTORY) + """ messages</p>
                <p>🔍 Logging: """ + ('Enabled' if ENABLE_DETAILED_LOGGING else 'Disabled') + """</p>
            </div>
            
            <h2>Features</h2>
            <ul>
                <li>Natural language processing</li>
                <li>Automatic category determination</li>
                <li>Multiple actions per message</li>
                <li>Full transaction editing</li>
                <li>Hindi/English support</li>
                <li>Budget & Loan Planning</li>
                <li>Recurring Expense Prediction</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return status_html

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "gemini_api": "configured" if GEMINI_API_KEY else "not_configured",
        "max_chat_history": MAX_CHAT_HISTORY,
        "logging_enabled": ENABLE_DETAILED_LOGGING
    }, 200

# ===========================
# MAIN
# ===========================

if __name__ == '__main__':
    init_users_db()
    
    print("\n" + "=" * 80)
    print("   🤖 WHATSAPP FINANCE MANAGER BOT")
    print("=" * 80)
    print("\n✅ System Status:")
    print(f"   • Database initialized")
    print(f"   • Gemini API: {'✅ Configured' if GEMINI_API_KEY else '❌ NOT SET'}")
    print(f"   • Max Chat History: {MAX_CHAT_HISTORY} messages")
    print(f"   • Detailed Logging: {'✅ Enabled' if ENABLE_DETAILED_LOGGING else '❌ Disabled'}")
    print(f"   • User Databases: {USER_DBS_DIR}/")
    
    print("\n📝 Features:")
    print("   • Natural language processing")
    print("   • Automatic category determination")
    print("   • Multiple actions per message")
    print("   • Full transaction editing")
    print("   • Budget & Loan Planning")
    print("   • Recurring Expense Prediction")
    
    print("\n🚀 Setup:")
    print("   • Set GEMINI_API_KEY environment variable")
    print("   • Configure Twilio webhook: http://your-server/webhook")
    print("   • For local: ngrok http 5000")
    
    print("\n🌐 Server starting on http://localhost:5000")
    print("=" * 80 + "\n")
    
    if not GEMINI_API_KEY:
        print("⚠️  WARNING: GEMINI_API_KEY not set!\n")
    
    app.run(port=5000, debug=True)