import database.db as db
from datetime import datetime
import pandas as pd
import io
from google_sync import send_data_to_sheets

PRODUCTS_LIST = [
    "HANZ (ATF)",
    "TEX 400 g.w ( BREAK FLUID ) DOT 3",
    "TEX 355 g.w ( BREAK FLUID ) DOT 3",
    "HANZ HYDRAULIC ( CH 68 )",
    "GEAR OIL ( 140 )"
]

# --- دالة إنشاء الفاتورة (بدون مزامنة تلقائية) ---
def create_invoice(client_id, quantity, price_per_unit, product_name, notes=""):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM Clients WHERE Client_ID = ?", (client_id,))
        if not cursor.fetchone():
            raise ValueError("العميل غير موجود")
        amount = quantity * price_per_unit
        cursor.execute('''
            INSERT INTO Invoices (Client_ID, Amount, Quantity, Created_At, Notes, ProductName, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (client_id, amount, quantity, datetime.now(), notes, product_name))
        conn.commit()
        invoice_id = cursor.lastrowid
        return invoice_id, amount

# --- دالة المزامنة التي يستدعيها الأدمن يدويًا ---
def sync_report_to_google_sheets(start_date, end_date, rep_id=None):
    data = get_report_data_for_google_sheets(start_date, end_date, rep_id)
    if not data:
        return False, "لا توجد بيانات للفترة المحددة"
    
    success = send_data_to_sheets(data)
    if success:
        return True, "تم رفع التقرير بنجاح إلى جوجل شيت"
    return False, "فشلت عملية المزامنة"

# --- دالة جلب البيانات لتنسيق جوجل شيت ---
def get_report_data_for_google_sheets(start_date, end_date, rep_id=None):
    invoices = get_invoices_for_period(start_date, end_date, rep_id)
    if not invoices: return None
    return [{
        'رقم الفاتورة': inv['id'],
        'التاريخ': inv['date'],
        'العميل': inv['client_name'],
        'المنتج': inv['product'],
        'العدد': inv['quantity'],
        'الإجمالي': inv['amount'],
        'المندوب': inv['rep_name']
    } for inv in invoices]

# --- الدوال المطلوبة لواجهة الأدمن والتقارير (لا تحذفها) ---

def get_all_reps_performance():
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.username, 
                   COALESCE(SUM(i.Amount), 0) as total_sales,
                   COALESCE(SUM(i.Quantity), 0) as total_qty,
                   COUNT(i.Invoice_ID) as invoice_count
            FROM Users u
            LEFT JOIN Clients c ON u.id = c.Assigned_Rep
            LEFT JOIN Invoices i ON c.Client_ID = i.Client_ID AND i.is_deleted = 0
            WHERE u.role = 'Rep'
            GROUP BY u.id
            ORDER BY total_sales DESC
        ''')
        results = cursor.fetchall()
        return [{"id": r[0], "username": r[1], "total_sales": r[2], "total_qty": r[3], "invoice_count": r[4]} for r in results]

def get_invoices_for_period(start_date, end_date, rep_id=None):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT i.Invoice_ID, c.Name, i.Amount, i.Quantity, i.Created_At, i.Notes, i.ProductName, u.username
            FROM Invoices i
            JOIN Clients c ON i.Client_ID = c.Client_ID
            JOIN Users u ON c.Assigned_Rep = u.id
            WHERE DATE(i.Created_At) BETWEEN DATE(?) AND DATE(?) AND i.is_deleted = 0
        '''
        params = [start_date, end_date]
        if rep_id:
            query += " AND c.Assigned_Rep = ?"
            params.append(rep_id)
        
        cursor.execute(query + " ORDER BY i.Created_At DESC", params)
        rows = cursor.fetchall()
        return [{"id": r[0], "client_name": r[1], "amount": r[2], "quantity": r[3], "date": r[4], "notes": r[5], "product": r[6], "rep_name": r[7]} for r in rows]

def get_overall_summary():
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(Amount), SUM(Quantity), COUNT(*) FROM Invoices WHERE is_deleted = 0')
        res = cursor.fetchone()
        return (res[0] or 0.0, res[1] or 0, res[2] or 0)

def get_best_selling_products(start_date, end_date):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ProductName, SUM(Quantity) as total_qty FROM Invoices
            WHERE DATE(Created_At) BETWEEN DATE(?) AND DATE(?) AND is_deleted = 0
            GROUP BY ProductName ORDER BY total_qty DESC LIMIT 5
        ''', (start_date, end_date))
        return cursor.fetchall()

def export_invoices_to_excel(start_date, end_date, rep_id=None):
    invoices = get_invoices_for_period(start_date, end_date, rep_id)
    if not invoices: return None
    df = pd.DataFrame(invoices)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()

def soft_delete_invoice(invoice_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Invoices SET is_deleted = 1 WHERE Invoice_ID = ?", (invoice_id,))
        conn.commit()
        return True, "تم الحذف"