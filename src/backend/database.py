import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "gallery.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poem_text TEXT NOT NULL,
            theme TEXT,
            mood TEXT,
            image_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_to_gallery(poem_text, theme, mood, image_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO gallery (poem_text, theme, mood, image_path)
        VALUES (?, ?, ?, ?)
    ''', (poem_text, theme, mood, image_path))
    conn.commit()
    conn.close()

def get_recent_art(limit=12):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM gallery ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
