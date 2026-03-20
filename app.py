"""
LinkUP - Chat Application Backend
Python Flask API Server
OTP delivered via Email (Gmail SMTP)
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import random
import string
import time
import os
import re
import resend

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# EMAIL CONFIGURATION  ← EDIT THESE TWO LINES
# ─────────────────────────────────────────────
#
# HOW TO GET A GMAIL APP PASSWORD (2 min):
#   1. Go to https://myaccount.google.com/security
#   2. Turn ON "2-Step Verification"
#   3. Go to https://myaccount.google.com/apppasswords
#   4. App: Mail  /  Device: Other → type "LinkUP"
#   5. Copy the 16-character password shown and paste below
#
# ⚠️  Use the APP PASSWORD, NOT your real Gmail password.
# ─────────────────────────────────────────────

SENDER_EMAIL    = os.environ.get("SENDER_EMAIL", "teamlinkup07@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "jate xjxe szbh ilky")    
SENDER_NAME     = "LinkUP"

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "linkup.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn   = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            created_at TEXT    DEFAULT (datetime('now')),
            last_seen  TEXT    DEFAULT (datetime('now')),
            is_online  INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_logs (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            email  TEXT    NOT NULL,
            otp    TEXT    NOT NULL,
            expiry INTEGER NOT NULL,
            used   INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_email   TEXT    NOT NULL,
            receiver_email TEXT    NOT NULL,
            message        TEXT    NOT NULL,
            timestamp      TEXT    DEFAULT (datetime('now')),
            is_read        INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialised.")

# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def current_ts():
    return int(time.time())

def valid_email(email):
    return bool(re.match(r'^[\w\.\+\-]+@[\w\-]+\.[a-z]{2,}$', email, re.I))

# ─────────────────────────────────────────────
# EMAIL SENDER
# ─────────────────────────────────────────────

def send_otp_email(to_email, to_name, otp):
    """Send OTP email via Resend API."""
    try:
        resend.api_key = os.environ.get("RESEND_API_KEY", "")

        html = f"""
        <div style="background:#0f141a;padding:40px;font-family:sans-serif;border-radius:16px;">
            <h1 style="color:#00e5ff;">LinkUP</h1>
            <p style="color:#e8edf3;">Hello {to_name},</p>
            <p style="color:#5a6a7a;">Your OTP for LinkUP login:</p>
            <div style="background:#161d26;border:2px solid rgba(0,229,255,0.3);
                        border-radius:12px;padding:24px;text-align:center;margin:20px 0;">
                <p style="color:#3a5060;font-size:12px;margin:0;">YOUR ONE-TIME PASSWORD</p>
                <p style="color:#00e5ff;font-size:40px;font-weight:800;
                           letter-spacing:10px;margin:10px 0;font-family:monospace;">{otp}</p>
            </div>
            <p style="color:#5a6a7a;">Expires in <strong style="color:#e8edf3;">5 minutes</strong></p>
            <p style="color:#5a6a7a;">Never share this code with anyone.</p>
        </div>
        """

        params = {
            "from": f"LinkUP <onboarding@resend.dev>",
            "to": [to_email],
            "subject": f"{otp} is your LinkUP login code",
            "html": html,
        }

        resend.Emails.send(params)
        print(f"[EMAIL] OTP delivered → {to_email}")
        return True, None

    except Exception as e:
        msg = f"Could not send email: {str(e)}"
        print(f"[EMAIL ERROR] {msg}")
        return False, msg

# ─────────────────────────────────────────────
# SERVE FRONTEND
# ─────────────────────────────────────────────

FRONTEND_DIR = os.path.abspath(os.path.dirname(__file__))

@app.route("/app/<path:filename>")
def serve_frontend(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route("/app/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "login.html")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "LinkUP Backend Running ✅", "version": "2.0"})

# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@app.route("/send-otp", methods=["POST"])
def send_otp():
    """POST { name, email } → generates OTP and emails it."""
    data = request.get_json() or {}

    name  = data.get("name",  "").strip()
    email = data.get("email", "").strip().lower()

    if not name:
        return jsonify({"success": False, "message": "Name is required."}), 400
    if not email or not valid_email(email):
        return jsonify({"success": False, "message": "Enter a valid email address."}), 400
    if SENDER_EMAIL == "your_gmail@gmail.com":
        return jsonify({
            "success": False,
            "message": "Email not configured on server. Open backend/app.py and set SENDER_EMAIL + SENDER_PASSWORD."
        }), 500

    otp    = generate_otp()
    expiry = current_ts() + 300   # 5 minutes

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE otp_logs SET used = 1 WHERE email = ?", (email,))
    cursor.execute(
        "INSERT INTO otp_logs (email, otp, expiry, used) VALUES (?, ?, ?, 0)",
        (email, otp, expiry)
    )
    conn.commit()
    conn.close()

    ok, err = send_otp_email(email, name, otp)
    if not ok:
        return jsonify({"success": False, "message": f"Failed to send email. {err}"}), 500

    return jsonify({
        "success": True,
        "message": f"OTP sent to {email}. Check your inbox (and spam folder)."
    })


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    """POST { name, email, otp } → verifies OTP, creates/logs in user."""
    data = request.get_json() or {}

    name  = data.get("name",  "").strip()
    email = data.get("email", "").strip().lower()
    otp   = data.get("otp",   "").strip()

    if not name or not email or not otp:
        return jsonify({"success": False, "message": "All fields are required."}), 400

    conn   = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM otp_logs WHERE email = ? AND used = 0 ORDER BY id DESC LIMIT 1",
        (email,)
    )
    record = cursor.fetchone()

    if not record:
        conn.close()
        return jsonify({"success": False, "message": "No OTP found. Please request a new one."}), 400

    if current_ts() > record["expiry"]:
        cursor.execute("UPDATE otp_logs SET used = 1 WHERE id = ?", (record["id"],))
        conn.commit()
        conn.close()
        return jsonify({"success": False, "message": "OTP expired. Please request a new one."}), 400

    if record["otp"] != otp:
        conn.close()
        return jsonify({"success": False, "message": "Incorrect OTP. Please try again."}), 400

    cursor.execute("UPDATE otp_logs SET used = 1 WHERE id = ?", (record["id"],))

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE users SET name=?, last_seen=datetime('now'), is_online=1 WHERE email=?",
            (name, email)
        )
        user_id = existing["id"]
    else:
        cursor.execute(
            "INSERT INTO users (name, email, is_online) VALUES (?, ?, 1)",
            (name, email)
        )
        user_id = cursor.lastrowid

    conn.commit()
    conn.close()
    print(f"[AUTH] {name} ({email}) logged in.")

    return jsonify({
        "success": True,
        "message": "Login successful!",
        "user": {"id": user_id, "name": name, "email": email}
    })


@app.route("/users", methods=["GET"])
def get_users():
    current = request.args.get("email", "").lower()
    conn    = get_db()
    cursor  = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, last_seen, is_online FROM users "
        "WHERE email != ? ORDER BY is_online DESC, name ASC",
        (current,)
    )
    users = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "users": users})


@app.route("/send-message", methods=["POST"])
def send_message():
    data     = request.get_json() or {}
    sender   = data.get("sender_email",   "").strip().lower()
    receiver = data.get("receiver_email", "").strip().lower()
    message  = data.get("message",        "").strip()

    if not sender or not receiver or not message:
        return jsonify({"success": False, "message": "All fields required."}), 400
    if len(message) > 1000:
        return jsonify({"success": False, "message": "Message too long (max 1000 chars)."}), 400

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (sender_email, receiver_email, message) VALUES (?, ?, ?)",
        (sender, receiver, message)
    )
    mid = cursor.lastrowid
    cursor.execute("UPDATE users SET last_seen=datetime('now') WHERE email=?", (sender,))
    conn.commit()
    cursor.execute("SELECT * FROM messages WHERE id=?", (mid,))
    new_msg = dict(cursor.fetchone())
    conn.close()
    return jsonify({"success": True, "message": new_msg})


@app.route("/get-messages", methods=["GET"])
def get_messages():
    sender   = request.args.get("sender",   "").lower()
    receiver = request.args.get("receiver", "").lower()
    since_id = request.args.get("since_id", 0, type=int)

    if not sender or not receiver:
        return jsonify({"success": False, "message": "sender and receiver required."}), 400

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, u.name AS sender_name
        FROM messages m
        LEFT JOIN users u ON m.sender_email = u.email
        WHERE ((m.sender_email=? AND m.receiver_email=?)
            OR (m.sender_email=? AND m.receiver_email=?))
          AND m.id > ?
        ORDER BY m.timestamp ASC, m.id ASC
        LIMIT 100
    """, (sender, receiver, receiver, sender, since_id))
    messages = [dict(r) for r in cursor.fetchall()]
    cursor.execute("""
        UPDATE messages SET is_read=1
        WHERE receiver_email=? AND sender_email=? AND is_read=0
    """, (sender, receiver))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "messages": messages})


@app.route("/set-online", methods=["POST"])
def set_online():
    data      = request.get_json() or {}
    email     = data.get("email", "").lower()
    is_online = data.get("is_online", 0)
    conn      = get_db()
    cursor    = conn.cursor()
    cursor.execute(
        "UPDATE users SET is_online=?, last_seen=datetime('now') WHERE email=?",
        (is_online, email)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("\n🚀  LinkUP Backend  (Email OTP Edition)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📡  http://0.0.0.0:5000")
    print("📱  Emulator  →  http://10.0.2.2:5000")
    print("📱  Real Dev  →  http://<YOUR_PC_IP>:5000")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port, debug=False)
