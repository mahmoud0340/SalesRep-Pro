# services/client_service.py
import database.db as db
import random
import string

def generate_client_code():
    """توليد كود عميل فريد مكون من 6 أحرف/أرقام"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM Clients WHERE Client_Code = ?", (code,))
            exists = cursor.fetchone()
        if not exists:
            return code

def add_client(name, phone, address, assigned_rep_id):
    client_code = generate_client_code()
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO Clients (Name, Phone, Address, Assigned_Rep, Client_Code)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, phone, address, assigned_rep_id, client_code))
            conn.commit()
            return True, client_code
        except Exception as e:
            return False, str(e)

def get_clients_by_rep(rep_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Client_ID, Name, Phone, Address, Client_Code
            FROM Clients WHERE Assigned_Rep = ?
        ''', (rep_id,))
        clients = cursor.fetchall()
        return [{"id": c[0], "name": c[1], "phone": c[2], "address": c[3], "code": c[4]} for c in clients]

def get_all_clients(limit=None, offset=None):
    """جلب كل العملاء مع دعم pagination"""
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT c.Client_ID, c.Name, c.Phone, c.Address, c.Client_Code, u.username, c.Assigned_Rep
            FROM Clients c
            JOIN Users u ON c.Assigned_Rep = u.id
        '''
        params = []
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = [limit, offset or 0]
        cursor.execute(query, params)
        clients = cursor.fetchall()
        return [{"id": cl[0], "name": cl[1], "phone": cl[2], "address": cl[3], "code": cl[4], "rep_name": cl[5], "rep_id": cl[6]} for cl in clients]

def get_total_clients_count():
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Clients")
        return cursor.fetchone()[0]

def get_client_by_id(client_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Client_ID, Name, Phone, Address, Client_Code, Assigned_Rep FROM Clients WHERE Client_ID = ?", (client_id,))
        client = cursor.fetchone()
        if client:
            return {"id": client[0], "name": client[1], "phone": client[2], "address": client[3], "code": client[4], "rep_id": client[5]}
        return None

def update_client(client_id, name, phone, address, rep_id=None):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        if rep_id:
            cursor.execute("UPDATE Clients SET Name = ?, Phone = ?, Address = ?, Assigned_Rep = ? WHERE Client_ID = ?",
                           (name, phone, address, rep_id, client_id))
        else:
            cursor.execute("UPDATE Clients SET Name = ?, Phone = ?, Address = ? WHERE Client_ID = ?",
                           (name, phone, address, client_id))
        conn.commit()

def get_clients_count_by_rep(rep_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Clients WHERE Assigned_Rep = ?", (rep_id,))
        return cursor.fetchone()[0]

def transfer_clients(old_rep_id, new_rep_id):
    """نقل جميع عملاء مندوب إلى مندوب آخر (قبل حذف المندوب القديم)"""
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Clients SET Assigned_Rep = ? WHERE Assigned_Rep = ?", (new_rep_id, old_rep_id))
        conn.commit()