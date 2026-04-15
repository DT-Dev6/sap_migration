import frappe
import pyodbc

# --- Connection Settings ---
# SERVER   = '192.168.12.1'      # or 'localhost'
# DATABASE = 'MPR'
# USERNAME = 'sa'
# PASSWORD = 'qwedsa'


SERVER   = 'localhost'      # or 'localhost'
DATABASE = 'MPR'
USERNAME = 'sap'
PASSWORD = 'Qwedsa@123'

# --- Optimized Connection String ---
CONN_STR = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    f'SERVER={SERVER};DATABASE={DATABASE};'
    f'UID={USERNAME};PWD={PASSWORD};'
    'TrustServerCertificate=yes;'
    # 'Connection Timeout=3;'
)


class MSSQL:
    def __init__(self):
        # try:
        self.conn = pyodbc.connect(CONN_STR, autocommit=True)
        self.cursor = self.conn.cursor()
        # except Exception as e:
        #     frappe.throw("❌ Error:", str(e))

    def select(self, query):
        # try:
        self.cursor.execute(query)
        columns = [col[0] for col in self.cursor.description]
        data = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        # data = self.cursor.fetchall()
        return data
        # except Exception as e:
        #     frappe.throw("❌ Data Error:", str(e))

    def execute(self, query):
        # try:
        self.cursor.execute(query)
        self.conn.commit()
        # except Exception as e:
        #     frappe.throw("❌ Execution Error:", e)



