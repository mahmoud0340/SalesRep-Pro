# database/db.py
import sqlite3
import hashlib
import re
from contextlib import contextmanager

DB_PATH = "salesrep.db"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password):
    if len(password) < 8:
        return False, "كلمة المرور يجب أن تكون 8 أحرف على الأقل"
    if not re.search(r"[A-Z]", password):
        return False, "كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل (A-Z)"
    if not re.search(r"[0-9]", password):
        return False, "كلمة المرور يجب أن تحتوي على رقم واحد على الأقل (0-9)"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "كلمة المرور يجب أن تحتوي على رمز خاص واحد على الأقل (مثل !@#$%^&*)"
    return True, "كلمة المرور قوية"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('Admin', 'Rep')),
                is_active INTEGER DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Clients (
                Client_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT NOT NULL,
                Phone TEXT,
                Address TEXT NOT NULL,
                Assigned_Rep INTEGER NOT NULL,
                Client_Code TEXT UNIQUE NOT NULL,
                Location TEXT DEFAULT '',
                FOREIGN KEY (Assigned_Rep) REFERENCES Users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Invoices (
                Invoice_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Client_ID INTEGER NOT NULL,
                Amount REAL NOT NULL,
                Quantity INTEGER NOT NULL,
                Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                Notes TEXT DEFAULT '',
                ProductName TEXT DEFAULT '',
                is_deleted INTEGER DEFAULT 0,
                FOREIGN KEY (Client_ID) REFERENCES Clients(Client_ID)
            )
        ''')
        conn.commit()
    upgrade_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_pass = hash_password("admin123")
            cursor.execute("INSERT INTO Users (username, password, role, is_active) VALUES (?, ?, ?, ?)",
                           ("admin", admin_pass, "Admin", 1))
            conn.commit()

def upgrade_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Clients)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'Location' not in columns:
            cursor.execute("ALTER TABLE Clients ADD COLUMN Location TEXT DEFAULT ''")
        
        cursor.execute("PRAGMA table_info(Invoices)")
        columns_inv = [col[1] for col in cursor.fetchall()]
        if 'ProductName' not in columns_inv:
            cursor.execute("ALTER TABLE Invoices ADD COLUMN ProductName TEXT DEFAULT ''")
        if 'is_deleted' not in columns_inv:
            cursor.execute("ALTER TABLE Invoices ADD COLUMN is_deleted INTEGER DEFAULT 0")
        conn.commit()

# باقي دوال المستخدمين كما هي (لم تتغير)
def get_user_by_username(username):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password, role, is_active FROM Users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            return {"id": user[0], "username": user[1], "password": user[2], "role": user[3], "is_active": user[4]}
        return None

def create_user(username, password, role):
    valid, msg = validate_password(password)
    if not valid:
        return False, msg
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            hashed = hash_password(password)
            cursor.execute("INSERT INTO Users (username, password, role, is_active) VALUES (?, ?, ?, ?)",
                           (username, hashed, role, 1))
            conn.commit()
            return True, "تم إنشاء المستخدم بنجاح"
        except sqlite3.IntegrityError:
            return False, "اسم المستخدم موجود بالفعل"

def update_user_password(user_id, new_password):
    valid, msg = validate_password(new_password)
    if not valid:
        return False, msg
    with get_db_connection() as conn:
        cursor = conn.cursor()
        hashed = hash_password(new_password)
        cursor.execute("UPDATE Users SET password = ? WHERE id = ?", (hashed, user_id))
        conn.commit()
        return True, "تم تحديث كلمة المرور"

def update_user_activation(user_id, is_active):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET is_active = ? WHERE id = ?", (is_active, user_id))
        conn.commit()

def get_all_users():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, is_active FROM Users")
        users = cursor.fetchall()
        return [{"id": u[0], "username": u[1], "role": u[2], "is_active": u[3]} for u in users]

def delete_user(user_id, current_user_id):
    if user_id == current_user_id:
        return False, "لا يمكن حذف حسابك الحالي"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Clients WHERE Assigned_Rep = ?", (user_id,))
        clients_count = cursor.fetchone()[0]
        if clients_count > 0:
            return False, f"لا يمكن حذف المستخدم لأنه مسؤول عن {clients_count} عميل. قم بنقل العملاء أولاً أو تعطيل الحساب."
        cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))
        conn.commit()
        return True, "تم حذف المستخدم بنجاح"

def get_active_reps():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM Users WHERE role = 'Rep' AND is_active = 1")
        return cursor.fetchall()