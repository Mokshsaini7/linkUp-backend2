/**
 * LinkUP – Login JS (Username/Password Edition)
 * No OTP, No Email — Simple and Fast!
 */

const BASE_URL = "https://linkup-backend2.onrender.com";

// ── HELPERS ───────────────────────────────────────────────────────────────

function showMsg(id, text, type = "error") {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = `msg-box ${type}`;
  el.classList.remove("hidden");
}

function hideMsg(id) {
  document.getElementById(id).classList.add("hidden");
}

function setLoading(btnId, on) {
  const btn    = document.getElementById(btnId);
  const label  = btn.querySelector(".btn-text");
  const loader = btn.querySelector(".btn-loader");
  btn.disabled = on;
  label.classList.toggle("hidden", on);
  loader.classList.toggle("hidden", !on);
}

function focusWrap(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.borderColor = "var(--accent)";
    el.style.boxShadow   = "0 0 0 3px var(--accent-glow)";
  }
}

function blurWrap(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.borderColor = "";
    el.style.boxShadow   = "";
  }
}

function togglePass(inputId, btn) {
  const input = document.getElementById(inputId);
  const isPass = input.type === "password";
  input.type = isPass ? "text" : "password";
  btn.style.opacity = isPass ? "1" : "0.5";
}

// ── TAB SWITCHING ─────────────────────────────────────────────────────────

function showLogin() {
  document.getElementById("loginForm").classList.remove("hidden");
  document.getElementById("registerForm").classList.add("hidden");
  document.getElementById("loginTab").classList.add("active");
  document.getElementById("registerTab").classList.remove("active");
  hideMsg("loginMsg");
}

function showRegister() {
  document.getElementById("registerForm").classList.remove("hidden");
  document.getElementById("loginForm").classList.add("hidden");
  document.getElementById("registerTab").classList.add("active");
  document.getElementById("loginTab").classList.remove("active");
  hideMsg("registerMsg");
}

// ── LOGIN ─────────────────────────────────────────────────────────────────

async function loginUser() {
  hideMsg("loginMsg");

  const username = document.getElementById("loginUsername").value.trim().toLowerCase();
  const password = document.getElementById("loginPassword").value.trim();

  if (!username) {
    showMsg("loginMsg", "Username daalo.");
    return;
  }
  if (!password) {
    showMsg("loginMsg", "Password daalo.");
    return;
  }

  setLoading("loginBtn", true);

  try {
    const res  = await fetch(`${BASE_URL}/login`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (data.success) {
      showMsg("loginMsg", "Login successful! Loading...", "success");
      sessionStorage.setItem("user", JSON.stringify(data.user));
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 800);
    } else {
      showMsg("loginMsg", data.message || "Login failed.", "error");
    }
  } catch (err) {
    showMsg("loginMsg", "Server se connect nahi ho pa raha. Backend chal raha hai?", "error");
  } finally {
    setLoading("loginBtn", false);
  }
}

// ── REGISTER ──────────────────────────────────────────────────────────────

async function registerUser() {
  hideMsg("registerMsg");

  const name     = document.getElementById("regName").value.trim();
  const username = document.getElementById("regUsername").value.trim().toLowerCase();
  const password = document.getElementById("regPassword").value.trim();
  const confirm  = document.getElementById("regConfirm").value.trim();

  // Validate
  if (!name) {
    showMsg("registerMsg", "Apna naam daalo.");
    return;
  }
  if (!username || username.length < 3) {
    showMsg("registerMsg", "Username kam se kam 3 characters ka hona chahiye.");
    return;
  }
  if (!/^[a-z0-9_]+$/.test(username)) {
    showMsg("registerMsg", "Username mein sirf letters, numbers aur underscore allowed hai.");
    return;
  }
  if (!password || password.length < 6) {
    showMsg("registerMsg", "Password kam se kam 6 characters ka hona chahiye.");
    return;
  }
  if (password !== confirm) {
    showMsg("registerMsg", "Dono passwords match nahi kar rahe!");
    return;
  }

  setLoading("registerBtn", true);

  try {
    const res  = await fetch(`${BASE_URL}/register`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ name, username, password })
    });

    const data = await res.json();

    if (data.success) {
      showMsg("registerMsg", "Account ban gaya! Ab login karo.", "success");
      // Clear fields
      document.getElementById("regName").value     = "";
      document.getElementById("regUsername").value = "";
      document.getElementById("regPassword").value = "";
      document.getElementById("regConfirm").value  = "";
      // Switch to login after 1.5s
      setTimeout(() => {
        showLogin();
        document.getElementById("loginUsername").value = username;
        document.getElementById("loginPassword").focus();
      }, 1500);
    } else {
      showMsg("registerMsg", data.message || "Registration failed.", "error");
    }
  } catch (err) {
    showMsg("registerMsg", "Server se connect nahi ho pa raha.", "error");
  } finally {
    setLoading("registerBtn", false);
  }
}
