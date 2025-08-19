from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_session import Session
from twilio.rest import Client
import pyodbc
import os
from datetime import datetime
from dotenv import load_dotenv
import re
from werkzeug.security import generate_password_hash, check_password_hash
from models.user_model import get_user_by_username, create_user

load_dotenv()

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Twilio credentials
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# SQL Server connection
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER="your server name";'
    'DATABASE="your database name";'
    'Trusted_Connection=yes;'
)
cursor = conn.cursor()

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)

        if user and check_password_hash(user['password_hash'], password):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        create_user(username, hashed_pw)
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear() 
    flash("You’ve been logged out.")
    return redirect(url_for('login'))
@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        return redirect(url_for('login'))

    flash_message = None
    latest_log = None
    just_sent = False

    if request.method == "POST":
        just_sent = True
        to_number = request.form["to_number"]
        message_body = request.form["message_body"]
        segment_count = (len(message_body) + 152) // 153
        cost_per_segment_inr = 6.94
        total_cost_inr = round(segment_count * cost_per_segment_inr, 2)

        if not to_number.startswith("+") or not to_number[1:].isdigit():
            status = "Failed: Invalid phone number format"
            message_sid = "N/A"
        else:
            try:
                message = client.messages.create(
                    body=message_body,
                    from_=TWILIO_NUMBER,
                    to=to_number,
                    status_callback='https://422a1445395a.ngrok-free.app/sms-status'
                )
                status = message.status
                message_sid = message.sid
            except Exception as e:
                status = strip_ansi(f"Failed: {str(e)}")[:255]
                message_sid = "N/A"

        cursor.execute("""
            INSERT INTO SmsLogs (SentAt, FromNumber, ToNumber, MessageBody, Status, MessageSid, SegmentCount, Cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now(), TWILIO_NUMBER, to_number, message_body, status[:255], message_sid, segment_count, total_cost_inr))
        conn.commit()
        session["last_sid"] = message_sid

   
    cursor.execute("""
        SELECT TOP 1 SentAt, FromNumber, ToNumber, MessageBody, Status, SegmentCount, Cost, MessageSid
        FROM SmsLogs
        ORDER BY SentAt DESC
    """)
    latest_log = cursor.fetchone()

    if latest_log:
        message_sid = latest_log[7]
        cursor.execute("SELECT Status FROM SmsLogs WHERE MessageSid = ?", (message_sid,))
        db_status_row = cursor.fetchone()
        db_status = db_status_row[0] if db_status_row else "unknown"

        if db_status.lower() == "delivered":
            flash_message = "✅ Message delivered successfully"
        elif db_status.lower() in ["queued", "sent"]:
            flash_message = f"⏳ Message is being delivered... (Status: {db_status})"
        else:
            flash_message = f"❌ Failed to send message: {db_status}"

    return render_template("index.html", username=session['user'], flash_message=flash_message, latest_log=latest_log, just_sent=just_sent)
@app.route("/logs")
def logs():
    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '').strip()
    date_filter = request.args.get('date', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10

    query = """
        SELECT SentAt, FromNumber, ToNumber, MessageBody, Status, SegmentCount, Cost
        FROM SmsLogs
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (ToNumber LIKE ? OR MessageBody LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]

    if date_filter:
        query += " AND CONVERT(date, SentAt) = ?"
        params.append(date_filter)

    query += " ORDER BY SentAt DESC"

  
    cursor.execute(query, params)
    logs_data = cursor.fetchall()

   
    total_logs = len(logs_data)
    total_pages = (total_logs + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page
    paginated_logs = logs_data[start:end]

    return render_template(
        "logs.html",
        logs=paginated_logs,
        page=page,
        total_pages=total_pages,
        search=search,
        date_filter=date_filter
    )
@app.route("/sms-status", methods=["POST"])
def sms_status():
    message_sid = request.form.get("MessageSid")
    message_status = request.form.get("MessageStatus")

    cursor.execute("""
        UPDATE SmsLogs SET Status = ?
        WHERE MessageSid = ?
    """, (message_status[:255], message_sid))
    conn.commit()

    return "OK", 200
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
@app.route("/inbox")
def inbox():
    cursor.execute("""
        SELECT ReceivedAt, FromNumber, ToNumber, MessageBody
        FROM IncomingMessages
        ORDER BY ReceivedAt DESC
    """)
    messages = cursor.fetchall()
    return render_template("inbox.html", messages=messages)
@app.route("/sms-inbound", methods=["POST"])
def sms_inbound():
    from_number = request.form.get("From")
    to_number = request.form.get("To")
    message_body = request.form.get("Body")
    timestamp = datetime.now()

    cursor.execute("""
        INSERT INTO IncomingMessages (ReceivedAt, FromNumber, ToNumber, MessageBody)
        VALUES (?, ?, ?, ?)
    """, (timestamp, from_number, to_number, message_body))
    conn.commit()

    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)