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
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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

SENDER_EMAIL    = "teamlinkup07@gmail.com"      # ← your Gmail here
SENDER_PASSWORD = "jate xjxe szbh ilky"       # ← 16-char App Password here
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
    """Send HTML OTP email via Gmail SMTP. Returns (ok, error_msg)."""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0d1117;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d1117;padding:40px 16px;">
  <tr><td align="center">
    <table width="480" cellpadding="0" cellspacing="0"
           style="background:#0f141a;border-radius:18px;border:1px solid rgba(255,255,255,0.08);overflow:hidden;max-width:100%;">

      <!-- Header bar -->
      <tr>
        <td style="background:linear-gradient(135deg,#0070ff,#00e5ff);padding:28px 36px;text-align:center;">
          <div style="display:inline-flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;background:rgba(0,0,0,0.2);border-radius:12px;
                        display:inline-flex;align-items:center;justify-content:center;">
              <span style="font-size:20px;">💬</span>
            </div>
            <span style="color:#000;font-size:26px;font-weight:800;letter-spacing:-1px;">LinkUP</span>
          </div>
          <p style="margin:6px 0 0;color:rgba(0,0,0,0.55);font-size:11px;
                    letter-spacing:2px;text-transform:uppercase;">Connect Instantly</p>
        </td>
      </tr>

      <!-- Body -->
      <tr>
        <td style="padding:36px 36px 28px;">
          <p style="margin:0 0 6px;color:#4a5a6a;font-size:12px;
                    text-transform:uppercase;letter-spacing:1px;">Hello,</p>
          <h2 style="margin:0 0 22px;color:#e8edf3;font-size:22px;font-weight:600;">
            {to_name} 👋
          </h2>
          <p style="margin:0 0 26px;color:#5a6a7a;font-size:14px;line-height:1.8;">
            You requested a login OTP for <strong style="color:#00e5ff;">LinkUP</strong>.<br>
            Use the code below to verify your account:
          </p>

          <!-- OTP display -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:26px;">
            <tr>
              <td style="background:#161d26;border:2px solid rgba(0,229,255,0.3);
                          border-radius:14px;padding:28px 20px;text-align:center;">
                <p style="margin:0 0 8px;font-size:11px;color:#3a5060;
                           letter-spacing:3px;text-transform:uppercase;">Your One-Time Password</p>
                <p style="margin:0;font-size:46px;font-weight:800;letter-spacing:12px;
                           color:#00e5ff;font-family:'Courier New',monospace;">{otp}</p>
              </td>
            </tr>
          </table>

          <!-- Info pills -->
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="background:#161d26;border-radius:10px;padding:13px 16px;margin-bottom:8px;">
                <span style="font-size:13px;color:#5a6a7a;">
                  ⏱ &nbsp;Expires in <strong style="color:#e8edf3;">5 minutes</strong>
                </span>
              </td>
            </tr>
            <tr><td style="height:8px;"></td></tr>
            <tr>
              <td style="background:#161d26;border-radius:10px;padding:13px 16px;">
                <span style="font-size:13px;color:#5a6a7a;">
                  🔒 &nbsp;Never share this code with anyone
                </span>
              </td>
            </tr>
          </table>

          <p style="margin:24px 0 0;font-size:12px;color:#2e3d4d;line-height:1.7;">
            If you did not request this, you can safely ignore this email.
          </p>
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="border-top:1px solid rgba(255,255,255,0.05);
                   padding:18px 36px;text-align:center;">
          <p style="margin:0;font-size:11px;color:#2a3a4a;">
            © 2024 LinkUP &nbsp;·&nbsp; Automated message — do not reply
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""

    plain = f"""LinkUP – Your OTP

Hello {to_name},

Your one-time password is: {otp}

It expires in 5 minutes. Do not share it with anyone.

If you didn't request this, ignore this email.

— LinkUP
"""

    try:
        msg             = MIMEMultipart("alternative")
        msg["Subject"]  = f"{otp} is your LinkUP login code"
        msg["From"]     = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"]       = to_email
        msg["X-Priority"] = "1"

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        pw = SENDER_PASSWORD.replace(" ", "")   # remove spaces from app password
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as srv:
            srv.ehlo()
            srv.starttls()
            srv.ehlo()
            srv.login(SENDER_EMAIL, pw)
            srv.sendmail(SENDER_EMAIL, to_email, msg.as_string())

        print(f"[EMAIL] OTP delivered → {to_email}")
        return True, None

    except smtplib.SMTPAuthenticationError:
        msg = ("Gmail authentication failed. "
               "Check SENDER_EMAIL and SENDER_PASSWORD in app.py. "
               "Make sure you're using a Gmail App Password, not your normal password.")
        print(f"[EMAIL ERROR] {msg}")
        return False, msg

    except smtplib.SMTPRecipientsRefused:
        msg = f"Email address {to_email} was rejected by Gmail."
        print(f"[EMAIL ERROR] {msg}")
        return False, msg

    except Exception as e:
        msg = f"Could not send email: {str(e)}"
        print(f"[EMAIL ERROR] {msg}")
        return False, msg

# ─────────────────────────────────────────────
# SERVE FRONTEND
# ─────────────────────────────────────────────

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

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
    app.run(host="0.0.0.0", port=5000, debug=True)
