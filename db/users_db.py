import sqlite3
from logger import log_info

def init_users_db():
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

def check_user_exists(phone):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = c.fetchone()
    conn.close()
    return user

def create_new_user(phone, unique_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (phone, unique_id, privacy_accepted) VALUES (?, ?, 'no')", (phone, unique_id))
    conn.commit()
    conn.close()
    init_user_database(phone)

def init_user_database(phone):
    # helper to create per-user DB when new user is created
    from db.user_db import init_user_db
    init_user_db(phone)

def get_privacy_status(phone):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT privacy_accepted FROM users WHERE phone = ?", (phone,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_privacy_acceptance(phone, accepted):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET privacy_accepted = ? WHERE phone = ?", (accepted, phone))
    conn.commit()
    conn.close()

def get_user_name(phone):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT name FROM users WHERE phone = ?", (phone,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "User"

def update_user_name(phone, new_name):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET name = ? WHERE phone = ?", (new_name, phone))
    conn.commit()
    conn.close()
