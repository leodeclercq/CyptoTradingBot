import sqlite3

DB_FILE = "C:\\...\\....db"

def init_db():
    """Initialise la base de données avec la table des prix et indicateurs."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS market_data (
                            time TEXT PRIMARY KEY,
                            open REAL,
                            high REAL,
                            low REAL,
                            close REAL,
                            TEMA20 REAL,
                            slope REAL,
                            TEMA50 REAL
                        )''')
        conn.commit()

def save_candle(data):
    """Sauvegarde une bougie dans la base de données."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT OR REPLACE INTO market_data
                        (time, open, high, low, close, TEMA20, slope, TEMA50)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()
