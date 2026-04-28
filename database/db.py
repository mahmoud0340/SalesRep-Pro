# database/db.py
import sqlite3
import hashlib
import re
from contextlib import contextmanager

DB_PATH = "salesrep.db"

# --------------------------- تشفير كلمة المرور ---------------------------
def hash_password(password):
    """تشفير كلمة المرور باستخدام SHA-256 (سيتم تحسينه لاحقاً)"""
    return hashlib.sha256(password.encode()).hexdigest()

# --------------------------- التحقق من قوة كلمة المرور ---------------------------
def validate_password(password):
    """
    التحقق من قوة كلمة المرور:
    - طول لا يقل عن 8 أحرف
    - يحتوي على حرف كبير واحد على الأقل
    - يحتوي على رقم واحد على الأقل
    - يحتوي على رمز خاص واحد على الأقل
    """
    if len(password) < 8:
        return False, "كلمة المرور يجب أن تكون 8 أحرف على الأقل"
    if not re.search(r"[A-Z]", password):
        return False, "كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل (A-Z)"
    if not re.search(r"[0-9]", password):
        return False, "كلمة المرور يجب أن تحتوي على رقم واحد على الأقل (0-9)"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "كلمة المرور يجب أن تحتوي على رمز خاص واحد على الأقل (مثل !@#$%^&*)"
    return True, "كلمة المرور قوية"

# --------------------------- إدارة الاتصال ---------------------------
@contextmanager
def get_db_connection():
    """مدير سياق لضمان إغلاق الاتصال تلقائياً"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

# --------------------------- تهيئة قاعدة البيانات والترقية ---------------------------
def init_db():
    """إنشاء الجداول إذا لم تكن موجودة، ثم ترقيتها"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('Admin', 'Rep')),
                is_active INTEGER DEFAULT 1
            )
        ''')
        # جدول العملاء
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Clients (
                Client_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT NOT NULL,
                Phone TEXT,
                Address TEXT NOT NULL,
                Assigned_Rep INTEGER NOT NULL,
                Client_Code TEXT UNIQUE NOT NULL,
                FOREIGN KEY (Assigned_Rep) REFERENCES Users(id)
            )
        ''')
        # جدول الفواتير
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Invoices (
                Invoice_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Client_ID INTEGER NOT NULL,
                Amount REAL NOT NULL,
                Quantity INTEGER NOT NULL,
                Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (Client_ID) REFERENCES Clients(Client_ID)
            )
        ''')
        conn.commit()

    # ترقية قاعدة البيانات (إضافة عمود Notes إذا لم يكن موجوداً)
    upgrade_db()

    # إضافة مدير افتراضي إذا لم يكن موجوداً (مع تجاوز التحقق من قوة كلمة المرور للمستخدم الأول)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_pass = hash_password("admin123")
            cursor.execute("INSERT INTO Users (username, password, role, is_active) VALUES (?, ?, ?, ?)",
                           ("admin", admin_pass, "Admin", 1))
            conn.commit()

def upgrade_db():
    """إضافة عمود Notes إلى جدول Invoices إذا لم يكن موجوداً"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Invoices)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'Notes' not in columns:
            cursor.execute("ALTER TABLE Invoices ADD COLUMN Notes TEXT DEFAULT ''")
            conn.commit()
            print("تم إضافة عمود Notes إلى جدول Invoices")

# --------------------------- دوال المستخدمين ---------------------------
def get_user_by_username(username):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password, role, is_active FROM Users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            return {"id": user[0], "username": user[1], "password": user[2], "role": user[3], "is_active": user[4]}
        return None

def create_user(username, password, role):
    """إنشاء مستخدم جديد مع التحقق من قوة كلمة المرور"""
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
    """تحديث كلمة المرور مع التحقق من القوة"""
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
    """حذف مستخدم فقط إذا لم يكن لديه عملاء مرتبطون"""
    if user_id == current_user_id:
        return False, "لا يمكن حذف حسابك الحالي"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # التحقق من وجود عملاء
        cursor.execute("SELECT COUNT(*) FROM Clients WHERE Assigned_Rep = ?", (user_id,))
        clients_count = cursor.fetchone()[0]
        if clients_count > 0:
            return False, f"لا يمكن حذف المستخدم لأنه مسؤول عن {clients_count} عميل/عملاء. قم بنقل العملاء أولاً أو تعطيل الحساب."
        
        cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))
        conn.commit()
        return True, "تم حذف المستخدم بنجاح"

def get_active_reps():
    """إرجاع قائمة المندوبين النشطين (لنقل العملاء)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM Users WHERE role = 'Rep' AND is_active = 1")
        return cursor.fetchall()