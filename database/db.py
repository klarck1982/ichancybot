import sqlite3
import os

DB_PATH = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            telegram_id INTEGER PRIMARY KEY,
            player_id TEXT,
            username TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            player_id TEXT,
            type TEXT,
            amount REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_player(telegram_id, player_id, username, email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO players (telegram_id, player_id, username, email)
        VALUES (?, ?, ?, ?)
    """, (telegram_id, player_id, username, email))
    conn.commit()
    conn.close()

def get_player(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"telegram_id": row[0], "player_id": row[1], "username": row[2], "email": row[3]}
    return None

def save_transaction(telegram_id, player_id, type_, amount, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO transactions (telegram_id, player_id, type, amount, status)
        VALUES (?, ?, ?, ?, ?)
    """, (telegram_id, player_id, type_, amount, status))
    conn.commit()
    conn.close()

def get_transactions(telegram_id, limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT type, amount, status, created_at FROM transactions
        WHERE telegram_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (telegram_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows
