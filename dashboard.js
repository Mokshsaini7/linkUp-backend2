/**
 * LinkUP – Dashboard JS
 * Handles chat UI, message polling, user list
 */

const BASE_URL = "https://linkup-backend2.onrender.com";

let currentUser = null;
let activeChat = null;
let allUsers = [];
let lastMsgId = 0;
let pollInterval = null;
let usersInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  const stored = sessionStorage.getItem("user");
  if (!stored) {
    window.location.href = "login.html";
    return;
  }

  currentUser = JSON.parse(stored);

  document.getElementById("myName").textContent = currentUser.name;
  document.getElementById("myPhone").textContent = "@" + currentUser.username;
  document.getElementById("myAvatar").textContent = getInitial(currentUser.name);

  setOnlineStatus(true);
  loadUsers();

  const isMobile = window.innerWidth < 768;
  if (isMobile) {
    document.getElementById("panelUsers").classList.remove("hidden");
    document.getElementById("panelChat").classList.add("hidden");
    document.getElementById("panelEmpty").classList.add("hidden");
  } else {
    document.getElementById("panelUsers").classList.remove("hidden");
    document.getElementById("panelEmpty").classList.remove("hidden");
    document.getElementById("panelChat").classList.add("hidden");
  }

  usersInterval = setInterval(loadUsers, 10000);
  window.addEventListener("beforeunload", () => setOnlineStatus(false));
});

function getInitial(name) {
  return name ? name.charAt(0).toUpperCase() : "?";
}

function formatTime(timestamp) {
  const d = new Date(timestamp);
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m`;
  const h = d.getHours().toString().padStart(2, "0");
  const m = d.getMinutes().toString().padStart(2, "0");
  return `${h}:${m}`;
}

async function setOnlineStatus(online) {
  try {
    await fetch(`${BASE_URL}/set-online`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: currentUser.username, is_online: online ? 1 : 0 })
    });
  } catch (e) {}
}

async function loadUsers() {
  try {
    const res = await fetch(`${BASE_URL}/users?username=${currentUser.username}`);
    const data = await res.json();
    if (data.success) {
      allUsers = data.users;
      renderUsers(allUsers);
    }
  } catch (err) {
    console.error("Failed to load users:", err);
  }
}

function filterUsers() {
  const query = document.getElementById("searchInput").value.toLowerCase();
  const filtered = allUsers.filter(u =>
    u.name.toLowerCase().includes(query) ||
    u.username.includes(query)
  );
  renderUsers(filtered);
}

function renderUsers(users) {
  const list = document.getElementById("usersList");
  const empty = document.getElementById("usersEmpty");

  if (!users.length) {
    list.innerHTML = "";
    list.appendChild(empty);
    empty.classList.remove("hidden");
    return;
  }

  list.innerHTML = "";

  users.forEach(user => {
    const div = document.createElement("div");
    div.className = `user-item${activeChat && activeChat.username === user.username ? " active" : ""}`;
    div.onclick = () => openChat(user);

    div.innerHTML = `
      <div class="user-item-avatar ${user.is_online ? 'online' : ''}">
        ${getInitial(user.name)}
      </div>
      <div class="user-item-info">
        <span class="user-item-name">${escapeHtml(user.name)}</span>
        <span class="user-item-preview">@${escapeHtml(user.username)}</span>
      </div>
      <div class="user-item-meta">
        <span class="user-item-time">${user.is_online ? "Online" : formatTime(user.last_seen)}</span>
      </div>
    `;

    list.appendChild(div);
  });
}

function openChat(user) {
  activeChat = user;
  lastMsgId = 0;

  document.getElementById("chatAvatar").textContent = getInitial(user.name);
  document.getElementById("chatName").textContent = user.name;
  document.getElementById("chatStatus").innerHTML = user.is_online
    ? `<span class="status-dot"></span> Online`
    : `<span class="status-dot" style="background:#5a6a7a"></span> Offline`;

  document.getElementById("messagesList").innerHTML = "";

  const isMobile = window.innerWidth < 768;
  if (isMobile) {
    document.getElementById("panelUsers").classList.add("hidden");
    document.getElementById("panelChat").classList.remove("hidden");
    document.getElementById("panelEmpty").classList.add("hidden");
  } else {
    document.getElementById("panelUsers").classList.remove("hidden");
    document.getElementById("panelChat").classList.remove("hidden");
    document.getElementById("panelEmpty").classList.add("hidden");
  }

  renderUsers(allUsers);
  loadMessages(true);

  clearInterval(pollInterval);
  pollInterval = setInterval(() => loadMessages(false), 2000);

  setTimeout(() => document.getElementById("msgInput").focus(), 200);
}

function backToUsers() {
  clearInterval(pollInterval);
  activeChat = null;

  const isMobile = window.innerWidth < 768;
  if (isMobile) {
    document.getElementById("panelUsers").classList.remove("hidden");
    document.getElementById("panelChat").classList.add("hidden");
    document.getElementById("panelEmpty").classList.add("hidden");
  }
  renderUsers(allUsers);
}

async function loadMessages(initial = false) {
  if (!activeChat) return;
  try {
    const url = `${BASE_URL}/get-messages?sender=${currentUser.username}&receiver=${activeChat.username}&since_id=${lastMsgId}`;
    const res = await fetch(url);
    const data = await res.json();
    if (data.success && data.messages.length > 0) {
      appendMessages(data.messages, initial);
      const ids = data.messages.map(m => m.id);
      lastMsgId = Math.max(lastMsgId, ...ids);
    }
  } catch (err) {
    console.error("Load messages error:", err);
  }
}

function appendMessages(messages, initial) {
  const list = document.getElementById("messagesList");
  const area = document.getElementById("messagesArea");
  const wasAtBottom = area.scrollHeight - area.scrollTop <= area.clientHeight + 60;

  messages.forEach(msg => {
    const isSent = msg.sender_username === currentUser.username;
    const wrapper = document.createElement("div");
    wrapper.className = `msg-wrapper ${isSent ? "sent" : "recv"}`;
    wrapper.dataset.msgId = msg.id;
    wrapper.innerHTML = `
      <div class="msg-bubble">${escapeHtml(msg.message)}</div>
      <div class="msg-meta">
        <span>${formatTime(msg.timestamp)}</span>
        ${isSent ? '<span class="msg-tick">✓✓</span>' : ''}
      </div>
    `;
    list.appendChild(wrapper);
  });

  if (initial || wasAtBottom) {
    setTimeout(() => { area.scrollTop = area.scrollHeight; }, 50);
  }
}

async function sendMessage() {
  if (!activeChat) return;
  const input = document.getElementById("msgInput");
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  autoResize(input);

  try {
    const res = await fetch(`${BASE_URL}/send-message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sender_username: currentUser.username,
        receiver_username: activeChat.username,
        message: text
      })
    });
    const data = await res.json();
    if (data.success) {
      appendMessages([data.message], false);
      lastMsgId = Math.max(lastMsgId, data.message.id);
    }
  } catch (err) {
    console.error("Send message error:", err);
    input.value = text;
  }
}

function handleMsgKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

function logout() {
  clearInterval(pollInterval);
  clearInterval(usersInterval);
  setOnlineStatus(false);
  sessionStorage.removeItem("user");
  window.location.href = "login.html";
}

function escapeHtml(str) {
  const map = { "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" };
  return String(str).replace(/[&<>"']/g, c => map[c]);
}
