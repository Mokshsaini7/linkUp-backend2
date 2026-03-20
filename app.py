"""
LinkUP - Chat Application Backend
Username + Password Authentication (No Email/OTP needed)
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import hashlib
import secrets

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "linkup.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Simple SHA256 password hashing with salt."""
    salt = "linkup_salt_2024"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table with username + password
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            username   TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now')),
            last_seen  TEXT    DEFAULT (datetime('now')),
            is_online  INTEGER DEFAULT 0
        )
    """)

    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_username  TEXT    NOT NULL,
            receiver_username TEXT   NOT NULL,
            message          TEXT    NOT NULL,
            timestamp        TEXT    DEFAULT (datetime('now')),
            is_read          INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialised.")

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
    return jsonify({"status": "LinkUP Backend Running", "version": "3.0"})

# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

@app.route("/register", methods=["POST"])
def register():
    """
    Register new user.
    Body: { name, username, password }
    """
    data = request.get_json() or {}

    name     = data.get("name",     "").strip()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    # Validate
    if not name:
        return jsonify({"success": False, "message": "Name is required."}), 400
    if not username or len(username) < 3:
        return jsonify({"success": False, "message": "Username must be at least 3 characters."}), 400
    if not username.isalnum() and "_" not in username:
        return jsonify({"success": False, "message": "Username can only have letters, numbers and underscore."}), 400
    if not password or len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400

    conn   = get_db()
    cursor = conn.cursor()

    # Check if username already exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"success": False, "message": "Username already taken. Try another one."}), 400

    # Create user
    hashed = hash_password(password)
    cursor.execute(
        "INSERT INTO users (name, username, password, is_online) VALUES (?, ?, ?, 1)",
        (name, username, hashed)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"[AUTH] New user registered: {name} (@{username})")

    return jsonify({
        "success": True,
        "message": "Account created successfully!",
        "user": {"id": user_id, "name": name, "username": username}
    })


@app.route("/login", methods=["POST"])
def login():
    """
    Login existing user.
    Body: { username, password }
    """
    data = request.get_json() or {}

    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required."}), 400

    conn   = get_db()
    cursor = conn.cursor()

    hashed = hash_password(password)
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, hashed)
    )
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"success": False, "message": "Wrong username or password."}), 400

    # Update online status
    cursor.execute(
        "UPDATE users SET is_online = 1, last_seen = datetime('now') WHERE username = ?",
        (username,)
    )
    conn.commit()
    conn.close()

    print(f"[AUTH] User logged in: {user['name']} (@{username})")

    return jsonify({
        "success": True,
        "message": "Login successful!",
        "user": {"id": user["id"], "name": user["name"], "username": username}
    })


# ─────────────────────────────────────────────
# USER ROUTES
# ─────────────────────────────────────────────

@app.route("/users", methods=["GET"])
def get_users():
    current = request.args.get("username", "").lower()
    conn    = get_db()
    cursor  = conn.cursor()
    cursor.execute(
        "SELECT id, name, username, last_seen, is_online FROM users "
        "WHERE username != ? ORDER BY is_online DESC, name ASC",
        (current,)
    )
    users = [dict(r) for r in cursor.fetchall()]
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
        "UPDATE users SET is_online = ?, last_seen = datetime('now') WHERE username = ?",
        (is_online, username)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ─────────────────────────────────────────────
# MESSAGE ROUTES
# ─────────────────────────────────────────────

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
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (sender_username, receiver_username, message) VALUES (?, ?, ?)",
        (sender, receiver, message)
    )
    mid = cursor.lastrowid
    cursor.execute(
        "UPDATE users SET last_seen = datetime('now') WHERE username = ?", (sender,)
    )
    conn.commit()
    cursor.execute("SELECT * FROM messages WHERE id = ?", (mid,))
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
        LEFT JOIN users u ON m.sender_username = u.username
        WHERE ((m.sender_username=? AND m.receiver_username=?)
            OR (m.sender_username=? AND m.receiver_username=?))
          AND m.id > ?
        ORDER BY m.timestamp ASC, m.id ASC
        LIMIT 100
    """, (sender, receiver, receiver, sender, since_id))
    messages = [dict(r) for r in cursor.fetchall()]
    cursor.execute("""
        UPDATE messages SET is_read = 1
        WHERE receiver_username = ? AND sender_username = ? AND is_read = 0
    """, (sender, receiver))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "messages": messages})


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print("\n🚀  LinkUP Backend  (Username/Password Edition)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📡  http://0.0.0.0:{port}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    app.run(host="0.0.0.0", port=port, debug=False)
