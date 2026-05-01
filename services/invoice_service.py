import sqlite3
from datetime import datetime
import pandas as pd
from database import db
from google_sync import send_data_to_sheets  # استيراد دالة المزامنة

def create_invoice(client_id, quantity, price_per_unit, product_name, notes=""):
    """
    إنشاء فاتورة وحفظها في قاعدة البيانات المحلية فقط.
    """
    try:
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # التأكد من وجود العميل
            cursor.execute("SELECT Name FROM Clients WHERE Client_ID = ?", (client_id,))
            client_row = cursor.fetchone()
            if not client_row:
                raise ValueError("العميل غير موجود")
            
            client_name = client_row[0]
            amount = quantity * price_per_unit
            current_time = datetime.now()

            # إدخال البيانات في جدول الفواتير
            cursor.execute('''
                INSERT INTO Invoices (Client_ID, Amount, Quantity, Created_At, Notes, ProductName, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            ''', (client_id, amount, quantity, current_time, notes, product_name))
            
            conn.commit()
            invoice_id = cursor.lastrowid
            
            return invoice_id, amount
    except Exception as e:
        print(f"Error in create_invoice: {e}")
        raise e

def get_report_data_for_google_sheets(start_date, end_date, rep_id=None):
    """
    جلب بيانات الفواتير من القاعدة المحلية لتحويلها لتقرير جاهز للمزامنة.
    """
    with db.get_db_connection() as conn:
        query = '''
            SELECT 
                i.Invoice_ID as "رقم الفاتورة",
                i.Created_At as "التاريخ",
                c.Name as "اسم العميل",
                i.ProductName as "المنتج",
                i.Quantity as "الكمية",
                i.Amount as "الإجمالي",
                u.Name as "المندوب"
            FROM Invoices i
            JOIN Clients c ON i.Client_ID = c.Client_ID
            JOIN Users u ON c.User_ID = u.User_ID
            WHERE date(i.Created_At) BETWEEN ? AND ?
            AND i.is_deleted = 0
        '''
        params = [start_date, end_date]
        if rep_id:
            query += " AND u.User_ID = ?"
            params.append(rep_id)
            
        df = pd.read_sql_query(query, conn)
        return df.to_dict(orient='records')

def sync_report_to_google_sheets(start_date, end_date, rep_id=None):
    """
    الدالة التي يستدعيها زر الأدمن لرفع التقرير.
    """
    data = get_report_data_for_google_sheets(start_date, end_date, rep_id)
    if not data:
        return False, "لا توجد بيانات للفترة المحددة"
    
    success = send_data_to_sheets(data)
    if success:
        return True, "تم رفع التقرير بنجاح إلى جوجل شيت"
    else:
        return False, "فشلت عملية المزامنة، تأكد من إعدادات الإنترنت والصلاحيات"

def export_invoices_to_excel(start_date, end_date, rep_id=None):
    """
    تصدير التقرير لملف Excel محلي (يحتاج مكتبة openpyxl).
    """
    with db.get_db_connection() as conn:
        query = "SELECT * FROM Invoices WHERE date(Created_At) BETWEEN ? AND ? AND is_deleted = 0"
        params = [start_date, end_date]
        df = pd.read_sql_query(query, conn)
        
        # حفظ الملف مؤقتاً للتنزيل
        file_path = "report.xlsx"
        df.to_excel(file_path, index=False, engine='openpyxl')
        return file_path