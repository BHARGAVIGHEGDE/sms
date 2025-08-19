import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=Pradeep;'
    'DATABASE=sms;'
    'Trusted_Connection=yes;'
)
cursor = conn.cursor()
def get_user_by_username(username):
    cursor.execute("SELECT username, password_hash FROM Users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row:
        return {'username': row[0], 'password_hash': row[1]}
    return None

def create_user(username, password_hash):
    cursor.execute("INSERT INTO Users (username, password_hash) VALUES (?, ?)", (username, password_hash))
    conn.commit()