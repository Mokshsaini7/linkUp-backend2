/**
 * LinkUP – Login JS (Email OTP Edition)
 * Handles email OTP send & verify flow.
 */

// ── CONFIG ────────────────────────────────────────────────────────────────
// Change this URL to match your backend:
//   Android Emulator : http://10.0.2.2:5000
//   Real Device      : http://192.168.x.x:5000   (your PC's local IP)
//   Browser testing  : http://localhost:5000
const BASE_URL = "http://192.168.1.103:5000";

let resendInterval = null;
let resendSeconds  = 60;   // 60-second cooldown before resend is allowed

// ── HELPERS ───────────────────────────────────────────────────────────────

function showMsg(id, text, type = "error") {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className   = `msg-box ${type}`;
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

// Highlight wrap border on focus
function focusWrap(id) {
  document.getElementById(id).style.borderColor = "var(--accent)";
  document.getElementById(id).style.boxShadow   = "0 0 0 3px var(--accent-glow)";
}
function blurWrap(id) {
  document.getElementById(id).style.borderColor = "";
  document.getElementById(id).style.boxShadow   = "";
}

// Mask email for display: jo***@gmail.com
function maskEmail(email) {
  const [local, domain] = email.split("@");
  if (!domain) return email;
  const visible = local.slice(0, 2);
  return `${visible}${"*".repeat(Math.max(local.length - 2, 3))}@${domain}`;
}

// ── STEP 1: SEND OTP ──────────────────────────────────────────────────────

async function sendOTP() {
  hideMsg("step1Msg");

  const name  = document.getElementById("nameInput").value.trim();
  const email = document.getElementById("emailInput").value.trim().toLowerCase();

  // Validate name
  if (!name) {
    showMsg("step1Msg", "Please enter your name.");
    document.getElementById("nameInput").focus();
    return;
  }

  // Validate email
  const emailRe = /^[\w.\+\-]+@[\w\-]+\.[a-z]{2,}$/i;
  if (!email || !emailRe.test(email)) {
    showMsg("step1Msg", "Please enter a valid email address.");
    document.getElementById("emailInput").focus();
    return;
  }

  setLoading("sendOtpBtn", true);

  try {
    const res  = await fetch(`${BASE_URL}/send-otp`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ name, email })
    });

    const data = await res.json();

    if (data.success) {
      showStep2(email);
    } else {
      showMsg("step1Msg", data.message || "Failed to send OTP.", "error");
    }
  } catch (err) {
    showMsg("step1Msg",
      "Cannot reach the server. Make sure the backend is running.", "error");
    console.error("sendOTP error:", err);
  } finally {
    setLoading("sendOtpBtn", false);
  }
}

// ── SHOW STEP 2 ───────────────────────────────────────────────────────────

function showStep2(email) {
  // Update the email badge
  document.getElementById("emailSentTo").textContent = maskEmail(email);

  // Switch panels
  document.getElementById("step1").classList.add("hidden");
  const s2 = document.getElementById("step2");
  s2.classList.remove("hidden");
  s2.classList.add("slide-in");

  // Focus first OTP box
  setTimeout(() => document.getElementById("o1").focus(), 120);

  // Start resend countdown
  startResendTimer();
}

// ── OTP BOX KEYBOARD HANDLING ─────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  const boxes = document.querySelectorAll(".otp-box");

  boxes.forEach((box, i) => {

    // Type a digit → move forward
    box.addEventListener("input", (e) => {
      e.target.value = e.target.value.replace(/\D/, "");   // digits only
      if (e.target.value.length === 1) {
        e.target.classList.add("filled");
        if (i < boxes.length - 1) {
          boxes[i + 1].focus();
        } else {
          // Last box filled – auto-submit
          verifyOTP();
        }
      } else {
        e.target.classList.remove("filled");
      }
    });

    // Backspace → go back
    box.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && e.target.value === "" && i > 0) {
        boxes[i - 1].focus();
        boxes[i - 1].value = "";
        boxes[i - 1].classList.remove("filled");
      }
    });

    // Paste full OTP
    box.addEventListener("paste", (e) => {
      e.preventDefault();
      const pasted = (e.clipboardData || window.clipboardData)
        .getData("text").replace(/\D/g, "").slice(0, 6);
      pasted.split("").forEach((ch, idx) => {
        if (boxes[idx]) {
          boxes[idx].value = ch;
          boxes[idx].classList.add("filled");
        }
      });
      if (pasted.length === 6) verifyOTP();
    });
  });

  // Enter key shortcuts
  document.getElementById("nameInput").addEventListener("keydown", e => {
    if (e.key === "Enter") document.getElementById("emailInput").focus();
  });
  document.getElementById("emailInput").addEventListener("keydown", e => {
    if (e.key === "Enter") sendOTP();
  });
});

// ── STEP 2: VERIFY OTP ────────────────────────────────────────────────────

async function verifyOTP() {
  hideMsg("step2Msg");

  const name  = document.getElementById("nameInput").value.trim();
  const email = document.getElementById("emailInput").value.trim().toLowerCase();
  const otp   = [...document.querySelectorAll(".otp-box")].map(b => b.value).join("");

  if (otp.length !== 6) {
    showMsg("step2Msg", "Please enter all 6 digits.", "error");
    return;
  }

  setLoading("verifyBtn", true);

  try {
    const res  = await fetch(`${BASE_URL}/verify-otp`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ name, email, otp })
    });

    const data = await res.json();

    if (data.success) {
      showMsg("step2Msg", "✓ Verified! Taking you in…", "success");

      // Save user to sessionStorage for dashboard to use
      sessionStorage.setItem("user", JSON.stringify(data.user));

      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 900);
    } else {
      showMsg("step2Msg", data.message || "Incorrect OTP.", "error");

      // Shake animation
      const wrap = document.querySelector(".otp-inputs");
      wrap.style.animation = "none";
      wrap.offsetHeight;                      // force reflow
      wrap.style.animation = "shake .4s ease";
    }
  } catch (err) {
    showMsg("step2Msg", "Cannot reach the server.", "error");
    console.error("verifyOTP error:", err);
  } finally {
    setLoading("verifyBtn", false);
  }
}

// ── BACK ──────────────────────────────────────────────────────────────────

function goBack() {
  clearInterval(resendInterval);

  document.getElementById("step2").classList.add("hidden");
  const s1 = document.getElementById("step1");
  s1.classList.remove("hidden");
  s1.classList.add("slide-in");

  // Clear OTP boxes
  document.querySelectorAll(".otp-box").forEach(b => {
    b.value = ""; b.classList.remove("filled");
  });

  hideMsg("step1Msg");
  hideMsg("step2Msg");
}

// ── RESEND TIMER ──────────────────────────────────────────────────────────

function startResendTimer() {
  resendSeconds = 60;
  const btn   = document.getElementById("resendBtn");
  const timer = document.getElementById("resendTimer");

  btn.disabled          = true;
  timer.textContent     = `(${resendSeconds}s)`;

  clearInterval(resendInterval);
  resendInterval = setInterval(() => {
    resendSeconds--;
    timer.textContent = resendSeconds > 0 ? `(${resendSeconds}s)` : "";
    if (resendSeconds <= 0) {
      clearInterval(resendInterval);
      btn.disabled = false;
    }
  }, 1000);
}

async function resendOTP() {
  const name  = document.getElementById("nameInput").value.trim();
  const email = document.getElementById("emailInput").value.trim().toLowerCase();

  hideMsg("step2Msg");

  try {
    const res  = await fetch(`${BASE_URL}/send-otp`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ name, email })
    });
    const data = await res.json();

    if (data.success) {
      showMsg("step2Msg", "New OTP sent! Check your inbox.", "success");
      startResendTimer();
      // Clear boxes
      document.querySelectorAll(".otp-box").forEach(b => {
        b.value = ""; b.classList.remove("filled");
      });
      document.getElementById("o1").focus();
    } else {
      showMsg("step2Msg", data.message || "Could not resend OTP.", "error");
    }
  } catch {
    showMsg("step2Msg", "Cannot reach the server.", "error");
  }
}

// ── SHAKE KEYFRAME ────────────────────────────────────────────────────────
const s = document.createElement("style");
s.textContent = `
@keyframes shake {
  0%,100% { transform: translateX(0); }
  20%     { transform: translateX(-8px); }
  40%     { transform: translateX(8px); }
  60%     { transform: translateX(-5px); }
  80%     { transform: translateX(5px); }
}`;
document.head.appendChild(s);
