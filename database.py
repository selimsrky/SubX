import sqlite3

DB_NAME = "subx.db"

def init_db():
    """Veritabanını başlatır ve gerekli tabloları oluşturur."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Kullanıcılar Tablosu (Başlangıç parası otomatik 10000 USD)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            cash_usd REAL NOT NULL DEFAULT 10000.0
        )
    ''')
    
    # Kullanıcı Portföyü Tablosu (Hisseler)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            user_id INTEGER,
            symbol TEXT,
            shares REAL,
            PRIMARY KEY (user_id, symbol)
        )
    ''')
    
    # Kullanıcılara Özel Abonelikler Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            renewal_day INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# --- KULLANICI İŞLEMLERİ ---
def create_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password, cash_usd) VALUES (?, ?, ?)', (username, password, 10000.0))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Kullanıcı adı zaten var
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# --- PORTFÖY VE CÜZDAN İŞLEMLERİ ---
def get_cash(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT cash_usd FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0.0

def update_cash(user_id, new_cash):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET cash_usd = ? WHERE id = ?', (new_cash, user_id))
    conn.commit()
    conn.close()

def get_portfolio(user_id):
    """Kullanıcının sahip olduğu hisseleri sözlük (dict) olarak döndürür {symbol: shares}"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT symbol, shares FROM portfolio WHERE user_id = ? AND shares > 0', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def update_portfolio(user_id, symbol, shares_change):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT shares FROM portfolio WHERE user_id = ? AND symbol = ?', (user_id, symbol))
    row = cursor.fetchone()
    current_shares = row[0] if row else 0.0
    new_shares = current_shares + shares_change
    
    if row:
        cursor.execute('UPDATE portfolio SET shares = ? WHERE user_id = ? AND symbol = ?', (new_shares, user_id, symbol))
    else:
        cursor.execute('INSERT INTO portfolio (user_id, symbol, shares) VALUES (?, ?, ?)', (user_id, symbol, new_shares))
        
    conn.commit()
    conn.close()

# --- ABONELİK İŞLEMLERİ (Artık kullanıcıya özel) ---
def add_subscription(user_id, name, amount, currency, renewal_day):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_subscriptions (user_id, name, amount, currency, renewal_day)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, name, amount, currency, renewal_day))
    conn.commit()
    conn.close()

def get_all_subscriptions(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, amount, currency, renewal_day FROM user_subscriptions WHERE user_id = ? ORDER BY renewal_day ASC', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_subscription(sub_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_subscriptions WHERE id = ?', (sub_id,))
    conn.commit()
    conn.close()