import sqlite3
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "mvp_state.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_state (
            slack_user_id TEXT PRIMARY KEY,
            ad_account_id TEXT,
            long_lived_token TEXT,
            preferences TEXT,
            last_sync_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def upsert_user_state(slack_user_id, ad_account_id, long_lived_token, preferences=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    prefs = json.dumps(preferences) if preferences else "{}"
    now = datetime.now()
    cursor.execute('''
        INSERT INTO user_state (slack_user_id, ad_account_id, long_lived_token, preferences, last_sync_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(slack_user_id) DO UPDATE SET
            ad_account_id=excluded.ad_account_id,
            long_lived_token=excluded.long_lived_token,
            preferences=excluded.preferences
    ''', (slack_user_id, ad_account_id, long_lived_token, prefs, now))
    conn.commit()
    conn.close()

def get_user_state(slack_user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_state WHERE slack_user_id = ?', (slack_user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_state')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_last_sync(slack_user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE user_state SET last_sync_at = ? WHERE slack_user_id = ?', (datetime.now(), slack_user_id))
    conn.commit()
    conn.close()

# Initialize DB on load
init_db()
