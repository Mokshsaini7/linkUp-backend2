"""
LinkUP - Chat Application Backend
Username + Password Auth + Supabase PostgreSQL
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import hashlib
import psycopg2
import psycopg2.extras

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def hash_password(password):
    salt = "linkup_salt_2024"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         SERIAL PRIMARY KEY,
            name       TEXT    NOT NULL,
            username   TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            last_seen  TIMESTAMP DEFAULT NOW(),
            is_online  INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id                SERIAL PRIMARY KEY,
            sender_username   TEXT NOT NULL,
            receiver_username TEXT NOT NULL,
            message           TEXT NOT NULL,
            timestamp         TIMESTAMP DEFAULT NOW(),
            is_read           INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("[DB] Supabase Database initialised.")

FRONTEND_DIR = os.path.abspath(os.path.dirname(__file__))

@app.route("/app/<path:filename>")
def serve_frontend(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route("/app/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "login.html")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "LinkUP Backend Running", "version": "4.0", "db": "Supabase"})

@app.route("/register", methods=["POST"])
def register():
    data     = request.get_json() or {}
    name     = data.get("name",     "").strip()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    if not name:
        return jsonify({"success": False, "message": "Name is required."}), 400
    if not username or len(username) < 3:
        return jsonify({"success": False, "message": "Username must be at least 3 characters."}), 400
    if not password or len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400

    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Username already taken."}), 400

    hashed = hash_password(password)
    cursor.execute(
        "INSERT INTO users (name, username, password, is_online) VALUES (%s, %s, %s, 1) RETURNING id",
        (name, username, hashed)
    )
    user_id = cursor.fetchone()["id"]
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Account created!",
        "user": {"id": user_id, "name": name, "username": username}
    })

@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json() or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required."}), 400

    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    hashed = hash_password(password)
    cursor.execute(
        "SELECT * FROM users WHERE username = %s AND password = %s",
        (username, hashed)
    )
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Wrong username or password."}), 400

    cursor.execute(
        "UPDATE users SET is_online = 1, last_seen = NOW() WHERE username = %s",
        (username,)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Login successful!",
        "user": {"id": user["id"], "name": user["name"], "username": username}
    })

@app.route("/users", methods=["GET"])
def get_users():
    current = request.args.get("username", "").lower()
    conn    = get_db()
    cursor  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(
        "SELECT id, name, username, last_seen, is_online FROM users "
        "WHERE username != %s ORDER BY is_online DESC, name ASC",
        (current,)
    )
    users = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify({"success": True, "users": users})

@app.route("/set-online", methods=["POST"])
def set_online():
    data      = request.get_json() or {}
    username  = data.get("username", "").lower()
    is_online = data.get("is_online", 0)
    conn      = get_db()
    cursor    = conn.cursor()
    cursor.execute(
        "UPDATE users SET is_online = %s, last_seen = NOW() WHERE username = %s",
        (is_online, username)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})

@app.route("/send-message", methods=["POST"])
def send_message():
    data     = request.get_json() or {}
    sender   = data.get("sender_username",   "").strip().lower()
    receiver = data.get("receiver_username", "").strip().lower()
    message  = data.get("message",           "").strip()

    if not sender or not receiver or not message:
        return jsonify({"success": False, "message": "All fields required."}), 400
    if len(message) > 1000:
        return jsonify({"success": False, "message": "Message too long."}), 400

    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(
        "INSERT INTO messages (sender_username, receiver_username, message) "
        "VALUES (%s, %s, %s) RETURNING *",
        (sender, receiver, message)
    )
    new_msg = dict(cursor.fetchone())
    cursor.execute(
        "UPDATE users SET last_seen = NOW() WHERE username = %s", (sender,)
    )
    conn.commit()
    cursor.close()
    conn.close()

    new_msg["timestamp"] = str(new_msg["timestamp"])
    return jsonify({"success": True, "message": new_msg})

@app.route("/get-messages", methods=["GET"])
def get_messages():
    sender   = request.args.get("sender",   "").lower()
    receiver = request.args.get("receiver", "").lower()
    since_id = request.args.get("since_id", 0, type=int)

    if not sender or not receiver:
        return jsonify({"success": False, "message": "sender and receiver required."}), 400

    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT m.*, u.name AS sender_name
        FROM messages m
        LEFT JOIN users u ON m.sender_username = u.username
        WHERE ((m.sender_username=%s AND m.receiver_username=%s)
            OR (m.sender_username=%s AND m.receiver_username=%s))
          AND m.id > %s
        ORDER BY m.timestamp ASC, m.id ASC
        LIMIT 100
    """, (sender, receiver, receiver, sender, since_id))

    messages = []
    for r in cursor.fetchall():
        msg = dict(r)
        msg["timestamp"] = str(msg["timestamp"])
        messages.append(msg)

    cursor.execute("""
        UPDATE messages SET is_read = 1
        WHERE receiver_username = %s AND sender_username = %s AND is_read = 0
    """, (sender, receiver))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "messages": messages})

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀  LinkUP v4.0 (Supabase Edition)")
    print(f"📡  Port: {port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
