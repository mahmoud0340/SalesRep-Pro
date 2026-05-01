# services/invoice_service.py
import database.db as db
from datetime import datetime, timedelta
import pandas as pd
import io
# --- إضافة استيراد دالة المزامنة ---
try:
    from google_sync import send_data_to_sheets
except ImportError:
    send_data_to_sheets = None
# --------------------------------

PRODUCTS_LIST = [
    "HANZ (ATF)",
    "TEX 400 g.w ( BREAK FLUID ) DOT 3",
    "TEX 355 g.w ( BREAK FLUID ) DOT 3",
    "HANZ HYDRAULIC ( CH 68 )",
    "GEAR OIL ( 140 )"
]

def create_invoice(client_id, quantity, price_per_unit, product_name, notes=""):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # جلب اسم العميل واسم المندوب لغرض المزامنة
        cursor.execute('''
            SELECT c.Name, u.username 
            FROM Clients c 
            JOIN Users u ON c.Assigned_Rep = u.id 
            WHERE c.Client_ID = ?
        ''', (client_id,))
        result = cursor.fetchone()
        
        if not result:
            raise ValueError("العميل غير موجود")
        
        client_name, rep_name = result
        amount = quantity * price_per_unit
        current_time = datetime.now()

        # 1. الحفظ في قاعدة البيانات المحلية (SQLite)
        cursor.execute('''
            INSERT INTO Invoices (Client_ID, Amount, Quantity, Created_At, Notes, ProductName, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (client_id, amount, quantity, current_time, notes, product_name))
        conn.commit()
        
        invoice_id = cursor.lastrowid

        # 2. المزامنة التلقائية مع جوجل شيت
        if send_data_to_sheets:
            data_to_sync = {
                "رقم الفاتورة": str(invoice_id),
                "التاريخ": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                "اسم العميل": client_name,
                "المنتج": product_name,
                "الكمية": quantity,
                "سعر الوحدة": price_per_unit,
                "الإجمالي": amount,
                "المندوب": rep_name,
                "ملاحظات": notes
            }
            # يتم الإرسال في الخلفية (سيظهر خطأ في الـ Terminal فقط إذا فشل)
            send_data_to_sheets(data_to_sync)

        return invoice_id, amount

# ... بقية الدوال كما هي دون تغيير ...
def get_invoices_by_client(client_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Invoice_ID, Amount, Quantity, Created_At, Notes, ProductName
            FROM Invoices WHERE Client_ID = ? AND is_deleted = 0
            ORDER BY Created_At DESC
        ''', (client_id,))
        invoices = cursor.fetchall()
        return [{"id": inv[0], "amount": inv[1], "quantity": inv[2], "date": inv[3], "notes": inv[4] or "", "product": inv[5] or ""} for inv in invoices]

def get_invoices_by_rep(rep_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT i.Invoice_ID, i.Client_ID, c.Name, i.Amount, i.Quantity, i.Created_At, i.Notes, i.ProductName
            FROM Invoices i
            JOIN Clients c ON i.Client_ID = c.Client_ID
            WHERE c.Assigned_Rep = ? AND i.is_deleted = 0
            ORDER BY i.Created_At DESC
        ''', (rep_id,))
        invoices = cursor.fetchall()
        return [{"id": inv[0], "client_id": inv[1], "client_name": inv[2], "amount": inv[3], "quantity": inv[4], "date": inv[5], "notes": inv[6] or "", "product": inv[7] or ""} for inv in invoices]

def get_rep_sales_summary(rep_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(i.Amount), SUM(i.Quantity), COUNT(i.Invoice_ID)
            FROM Invoices i
            JOIN Clients c ON i.Client_ID = c.Client_ID
            WHERE c.Assigned_Rep = ? AND i.is_deleted = 0
        ''', (rep_id,))
        total_amount, total_qty, invoice_count = cursor.fetchone()
        return (total_amount or 0.0, total_qty or 0, invoice_count or 0)

def get_overall_summary():
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(Amount), SUM(Quantity), COUNT(*) FROM Invoices WHERE is_deleted = 0')
        total_amount, total_qty, invoice_count = cursor.fetchone()
        return (total_amount or 0.0, total_qty or 0, invoice_count or 0)

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

def get_best_selling_products(start_date, end_date):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ProductName, SUM(Quantity) as total_qty
            FROM Invoices
            WHERE DATE(Created_At) BETWEEN DATE(?) AND DATE(?) AND ProductName != '' AND is_deleted = 0
            GROUP BY ProductName
            ORDER BY total_qty DESC
            LIMIT 5
        ''', (start_date, end_date))
        return cursor.fetchall()

def get_invoices_for_period(start_date, end_date, rep_id=None):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        if rep_id:
            cursor.execute('''
                SELECT i.Invoice_ID, c.Name as ClientName, i.Amount, i.Quantity, i.Created_At, i.Notes, i.ProductName, u.username as RepName, c.Location
                FROM Invoices i
                JOIN Clients c ON i.Client_ID = c.Client_ID
                JOIN Users u ON c.Assigned_Rep = u.id
                WHERE DATE(i.Created_At) BETWEEN DATE(?) AND DATE(?) AND c.Assigned_Rep = ? AND i.is_deleted = 0
                ORDER BY i.Created_At
            ''', (start_date, end_date, rep_id))
        else:
            cursor.execute('''
                SELECT i.Invoice_ID, c.Name as ClientName, i.Amount, i.Quantity, i.Created_At, i.Notes, i.ProductName, u.username as RepName, c.Location
                FROM Invoices i
                JOIN Clients c ON i.Client_ID = c.Client_ID
                JOIN Users u ON c.Assigned_Rep = u.id
                WHERE DATE(i.Created_At) BETWEEN DATE(?) AND DATE(?) AND i.is_deleted = 0
                ORDER BY i.Created_At
            ''', (start_date, end_date))
        rows = cursor.fetchall()
        return [{"id": r[0], "client_name": r[1], "amount": r[2], "quantity": r[3], "date": r[4], "notes": r[5] or "", "product": r[6] or "", "rep_name": r[7], "location": r[8] or ""} for r in rows]

def export_invoices_to_csv(start_date, end_date, rep_id=None):
    invoices = get_invoices_for_period(start_date, end_date, rep_id)
    output = io.StringIO()
    performance = get_all_reps_performance()
    if rep_id:
        performance = [p for p in performance if p['id'] == rep_id]
    total_sales = sum(i['amount'] for i in invoices)
    total_qty = sum(i['quantity'] for i in invoices)
    total_invoices = len(invoices)
    output.write("=== تقرير المبيعات ===\n")
    output.write(f"الفترة: {start_date} إلى {end_date}\n")
    output.write(f"إجمالي المبيعات المالية: {total_sales:.2f} ج.م\n")
    output.write(f"إجمالي الكميات المباعة: {total_qty}\n")
    output.write(f"عدد الفواتير: {total_invoices}\n\n")
    output.write("=== ترتيب المناديب حسب المبيعات ===\n")
    for p in performance:
        output.write(f"{p['username']}: {p['total_sales']:.2f} ج.م (فواتير: {p['invoice_count']})\n")
    output.write("\n")
    best_products = get_best_selling_products(start_date, end_date)
    output.write("=== أكثر المنتجات مبيعاً ===\n")
    for prod in best_products:
        output.write(f"{prod[0]}: {prod[1]} قطعة\n")
    output.write("\n")
    output.write("=== تفاصيل الفواتير ===\n")
    output.write("رقم الفاتورة;التاريخ;العميل;الموقع;المنتج;العدد;السعر;الإجمالي;الملاحظات;المندوب\n")
    for inv in invoices:
        price_per_unit = inv['amount'] / inv['quantity'] if inv['quantity'] > 0 else 0
        output.write(f"{inv['id']};{inv['date']};{inv['client_name']};{inv['location']};{inv['product']};{inv['quantity']};{price_per_unit:.2f};{inv['amount']:.2f};{inv['notes']};{inv['rep_name']}\n")
    return output.getvalue().encode('utf-8-sig')

def export_invoices_to_excel(start_date, end_date, rep_id=None):
    invoices = get_invoices_for_period(start_date, end_date, rep_id)
    if not invoices:
        return None
    total_sales = sum(i['amount'] for i in invoices)
    total_qty = sum(i['quantity'] for i in invoices)
    total_invoices = len(invoices)
    performance_data = []
    if rep_id is None:
        rep_sales = {}
        for inv in invoices:
            rep_name = inv['rep_name']
            if rep_name not in rep_sales:
                rep_sales[rep_name] = {'total_sales': 0, 'invoice_count': 0, 'total_qty': 0}
            rep_sales[rep_name]['total_sales'] += inv['amount']
            rep_sales[rep_name]['invoice_count'] += 1
            rep_sales[rep_name]['total_qty'] += inv['quantity']
        performance_data = [{'name': name, **data} for name, data in rep_sales.items()]
        performance_data.sort(key=lambda x: x['total_sales'], reverse=True)
    else:
        performance_data = [{'name': invoices[0]['rep_name'] if invoices else '', 'total_sales': total_sales, 'invoice_count': total_invoices, 'total_qty': total_qty}]
    products_sales = {}
    for inv in invoices:
        if inv['product']:
            products_sales[inv['product']] = products_sales.get(inv['product'], 0) + inv['quantity']
    best_products = sorted(products_sales.items(), key=lambda x: x[1], reverse=True)[:5]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_data = {
            'المعيار': ['الفترة', 'إجمالي المبيعات (ج.م)', 'إجمالي الكميات المباعة', 'عدد الفواتير'],
            'القيمة': [f'{start_date} إلى {end_date}', f'{total_sales:,.2f}', total_qty, total_invoices]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='ملخص', index=False)
        if performance_data:
            df_reps = pd.DataFrame(performance_data)
            df_reps.columns = ['اسم المندوب', 'إجمالي المبيعات (ج.م)', 'عدد الفواتير', 'إجمالي الكميات']
            df_reps.to_excel(writer, sheet_name='ترتيب المندوبين', index=False)
        if best_products:
            df_products = pd.DataFrame(best_products, columns=['المنتج', 'الكمية المباعة'])
            df_products.to_excel(writer, sheet_name='أكثر المنتجات مبيعاً', index=False)
        details = []
        for inv in invoices:
            price_per_unit = inv['amount'] / inv['quantity'] if inv['quantity'] > 0 else 0
            date_val = inv['date']
            if isinstance(date_val, str):
                date_str = date_val
            else:
                date_str = date_val.strftime('%Y-%m-%d %H:%M:%S')
            details.append({
                'رقم الفاتورة': inv['id'],
                'التاريخ': date_str,
                'العميل': inv['client_name'],
                'الموقع': inv['location'],
                'المنتج': inv['product'],
                'العدد': inv['quantity'],
                'سعر الوحدة (ج.م)': f"{price_per_unit:.2f}",
                'الإجمالي (ج.م)': f"{inv['amount']:.2f}",
                'الملاحظات': inv['notes'],
                'المندوب': inv['rep_name']
            })
        df_details = pd.DataFrame(details)
        df_details.to_excel(writer, sheet_name='تفاصيل الفواتير', index=False)
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column_cells in worksheet.columns:
                max_length = 0
                for cell in column_cells:
                    try:
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 40)
                worksheet.column_dimensions[column_cells[0].column_letter].width = adjusted_width
    output.seek(0)
    return output.getvalue()

def get_last_invoice_by_client(client_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Invoice_ID, Amount, Quantity, Created_At, Notes, ProductName
            FROM Invoices
            WHERE Client_ID = ? AND is_deleted = 0
            ORDER BY Created_At DESC
            LIMIT 1
        ''', (client_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "amount": row[1],
                "quantity": row[2],
                "date": row[3],
                "notes": row[4] or "",
                "product": row[5] or ""
            }
        return None

def get_report_data_for_google_sheets(start_date, end_date, rep_id=None):
    invoices = get_invoices_for_period(start_date, end_date, rep_id)
    if not invoices:
        return None
    report_rows = []
    for inv in invoices:
        price_per_unit = inv['amount'] / inv['quantity'] if inv['quantity'] > 0 else 0
        date_val = inv['date']
        if isinstance(date_val, str):
            date_str = date_val
        else:
            date_str = date_val.strftime('%Y-%m-%d %H:%M:%S')
        report_rows.append({
            'رقم الفاتورة': inv['id'],
            'التاريخ': date_str,
            'العميل': inv['client_name'],
            'الموقع': inv['location'],
            'المنتج': inv['product'],
            'العدد': inv['quantity'],
            'سعر_الوحدة': price_per_unit,
            'الإجمالي': inv['amount'],
            'الملاحظات': inv['notes'],
            'المندوب': inv['rep_name']
        })
    return report_rows

def soft_delete_invoice(invoice_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Invoices SET is_deleted = 1 WHERE Invoice_ID = ?", (invoice_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return False, "الفاتورة غير موجودة"
        return True, "تم حذف الفاتورة بنجاح"