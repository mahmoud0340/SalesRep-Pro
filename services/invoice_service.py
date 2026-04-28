# services/invoice_service.py
import database.db as db
from datetime import datetime, timedelta
import pandas as pd

def create_invoice(client_id, quantity, price_per_unit, notes=""):
    """إنشاء فاتورة جديدة مع التحقق من وجود العميل وإضافة ملاحظات"""
    # التحقق من وجود العميل
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM Clients WHERE Client_ID = ?", (client_id,))
        if not cursor.fetchone():
            raise ValueError("العميل غير موجود")

        amount = quantity * price_per_unit
        cursor.execute('''
            INSERT INTO Invoices (Client_ID, Amount, Quantity, Created_At, Notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (client_id, amount, quantity, datetime.now(), notes))
        conn.commit()
        invoice_id = cursor.lastrowid
        return invoice_id, amount

def get_invoices_by_client(client_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Invoice_ID, Amount, Quantity, Created_At, Notes
            FROM Invoices WHERE Client_ID = ?
            ORDER BY Created_At DESC
        ''', (client_id,))
        invoices = cursor.fetchall()
        return [{"id": inv[0], "amount": inv[1], "quantity": inv[2], "date": inv[3], "notes": inv[4] or ""} for inv in invoices]

def get_invoices_by_rep(rep_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT i.Invoice_ID, i.Client_ID, c.Name, i.Amount, i.Quantity, i.Created_At, i.Notes
            FROM Invoices i
            JOIN Clients c ON i.Client_ID = c.Client_ID
            WHERE c.Assigned_Rep = ?
            ORDER BY i.Created_At DESC
        ''', (rep_id,))
        invoices = cursor.fetchall()
        return [{"id": inv[0], "client_id": inv[1], "client_name": inv[2], "amount": inv[3], "quantity": inv[4], "date": inv[5], "notes": inv[6] or ""} for inv in invoices]

def get_rep_sales_summary(rep_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(i.Amount), SUM(i.Quantity)
            FROM Invoices i
            JOIN Clients c ON i.Client_ID = c.Client_ID
            WHERE c.Assigned_Rep = ?
        ''', (rep_id,))
        total_amount, total_qty = cursor.fetchone()
        return (total_amount or 0.0, total_qty or 0)

def get_overall_summary():
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(Amount), SUM(Quantity) FROM Invoices')
        total_amount, total_qty = cursor.fetchone()
        return (total_amount or 0.0, total_qty or 0)

def get_all_reps_performance():
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.username, 
                   COALESCE(SUM(i.Amount), 0) as total_sales,
                   COALESCE(SUM(i.Quantity), 0) as total_qty
            FROM Users u
            LEFT JOIN Clients c ON u.id = c.Assigned_Rep
            LEFT JOIN Invoices i ON c.Client_ID = i.Client_ID
            WHERE u.role = 'Rep'
            GROUP BY u.id
        ''')
        results = cursor.fetchall()
        return [{"id": r[0], "username": r[1], "total_sales": r[2], "total_qty": r[3]} for r in results]

# --------------------------- دوال التقارير (CSV) ---------------------------
def get_invoices_for_period(start_date, end_date, rep_id=None):
    """
    جلب الفواتير في فترة زمنية معينة.
    إذا تم تحديد rep_id، يتم التصفية حسب المندوب.
    """
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        if rep_id:
            cursor.execute('''
                SELECT i.Invoice_ID, c.Name as ClientName, i.Amount, i.Quantity, i.Created_At, i.Notes, u.username as RepName
                FROM Invoices i
                JOIN Clients c ON i.Client_ID = c.Client_ID
                JOIN Users u ON c.Assigned_Rep = u.id
                WHERE DATE(i.Created_At) BETWEEN DATE(?) AND DATE(?) AND c.Assigned_Rep = ?
                ORDER BY i.Created_At
            ''', (start_date, end_date, rep_id))
        else:
            cursor.execute('''
                SELECT i.Invoice_ID, c.Name as ClientName, i.Amount, i.Quantity, i.Created_At, i.Notes, u.username as RepName
                FROM Invoices i
                JOIN Clients c ON i.Client_ID = c.Client_ID
                JOIN Users u ON c.Assigned_Rep = u.id
                WHERE DATE(i.Created_At) BETWEEN DATE(?) AND DATE(?)
                ORDER BY i.Created_At
            ''', (start_date, end_date))
        rows = cursor.fetchall()
        return [{"id": r[0], "client_name": r[1], "amount": r[2], "quantity": r[3], "date": r[4], "notes": r[5] or "", "rep_name": r[6]} for r in rows]

def export_invoices_to_csv(start_date, end_date, rep_id=None):
    """تصدير الفواتير إلى DataFrame ثم تحويلها إلى CSV"""
    invoices = get_invoices_for_period(start_date, end_date, rep_id)
    if not invoices:
        return None
    df = pd.DataFrame(invoices)
    # إعادة تسمية الأعمدة للغة العربية
    df.columns = ["رقم الفاتورة", "اسم العميل", "المبلغ", "العدد", "التاريخ", "الملاحظات", "اسم المندوب"]
    return df.to_csv(index=False).encode('utf-8')