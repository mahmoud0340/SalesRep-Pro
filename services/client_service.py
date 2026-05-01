# services/client_service.py
import database.db as db

def get_next_client_code():
    """توليد كود عميل تسلسلي من C001 فصاعداً"""
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Client_Code FROM Clients ORDER BY Client_Code DESC LIMIT 1")
        last = cursor.fetchone()
        if not last:
            return "C001"
        last_code = last[0]
        if last_code.startswith('C'):
            try:
                num = int(last_code[1:])
                return f"C{num+1:03d}"
            except:
                return "C001"
        return "C001"

def add_client(name, phone, address, assigned_rep_id, location=""):
    client_code = get_next_client_code()
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO Clients (Name, Phone, Address, Assigned_Rep, Client_Code, Location)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, phone, address, assigned_rep_id, client_code, location))
            conn.commit()
            return True, client_code
        except Exception as e:
            return False, str(e)

def get_clients_by_rep(rep_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Client_ID, Name, Phone, Address, Client_Code, Location
            FROM Clients WHERE Assigned_Rep = ?
        ''', (rep_id,))
        clients = cursor.fetchall()
        return [{"id": c[0], "name": c[1], "phone": c[2], "address": c[3], "code": c[4], "location": c[5] or ""} for c in clients]

def get_all_clients(limit=None, offset=None):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT c.Client_ID, c.Name, c.Phone, c.Address, c.Client_Code, u.username, c.Assigned_Rep, c.Location
            FROM Clients c
            JOIN Users u ON c.Assigned_Rep = u.id
        '''
        params = []
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = [limit, offset or 0]
        cursor.execute(query, params)
        clients = cursor.fetchall()
        return [{"id": cl[0], "name": cl[1], "phone": cl[2], "address": cl[3], "code": cl[4], "rep_name": cl[5], "rep_id": cl[6], "location": cl[7] or ""} for cl in clients]

def get_total_clients_count():
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Clients")
        return cursor.fetchone()[0]

def get_client_by_id(client_id):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Client_ID, Name, Phone, Address, Client_Code, Assigned_Rep, Location FROM Clients WHERE Client_ID = ?", (client_id,))
        client = cursor.fetchone()
        if client:
            return {"id": client[0], "name": client[1], "phone": client[2], "address": client[3], "code": client[4], "rep_id": client[5], "location": client[6] or ""}
        return None

def update_client(client_id, name, phone, address, location=None, rep_id=None):
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        if rep_id and location is not None:
            cursor.execute("UPDATE Clients SET Name = ?, Phone = ?, Address = ?, Assigned_Rep = ?, Location = ? WHERE Client_ID = ?",
                           (name, phone, address, rep_id, location, client_id))
        elif rep_id:
            cursor.execute("UPDATE Clients SET Name = ?, Phone = ?, Address = ?, Assigned_Rep = ? WHERE Client_ID = ?",
                           (name, phone, address, rep_id, client_id))
        elif location is not None:
            cursor.execute("UPDATE Clients SET Name = ?, Phone = ?, Address = ?, Location = ? WHERE Client_ID = ?",
                           (name, phone, address, location, client_id))
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
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Clients SET Assigned_Rep = ? WHERE Assigned_Rep = ?", (new_rep_id, old_rep_id))
        conn.commit()