let token = null;
let ws = null;
let username = null;

let lastSent = 0;
const SEND_COOLDOWN = 1000;

const loginScreen = document.getElementById("loginScreen");
const chatScreen = document.getElementById("chatScreen");
const messages = document.getElementById("messages");
const onlineList = document.getElementById("onlineList");
const typingIndicator = document.getElementById("typingIndicator");

let typingTimeout = null;
let isTyping = false;

document.getElementById("loginBtn").onclick = login;

async function login() {
  username = document.getElementById("user").value;
  const password = document.getElementById("pass").value;

  const res = await fetch("/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username, password})
  });

  if (!res.ok) {
    alert("Invalid login");
    return;
  }

  const data = await res.json();
  token = data.token;

  loginScreen.style.display = "none";
  chatScreen.style.display = "flex";

  connectWS();
}

function connectWS() {
  ws = new WebSocket(`wss://${location.host}/ws?token=${token}`);

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === "chat") {
      addMessage(msg.data.from, msg.data.text, msg.data.from === username);
    }

    if (msg.type === "user_joined") {
      addSystem(`${msg.data.user} joined`);
    }

    if (msg.type === "user_left") {
      addSystem(`${msg.data.user} left`);
    }

    if (msg.type === "online_list") {
      onlineList.innerHTML = "";
      msg.data.users.forEach(u => {
        const li = document.createElement("li");
        li.textContent = u;
        onlineList.appendChild(li);
      });
    }

    if (msg.type === "typing") {
      showTyping(msg.data.user, msg.data.isTyping);
    }
  };

  ws.onclose = () => {
    addSystem("Disconnected. Reconnecting...");
    setTimeout(connectWS, 2000);
  };
}

document.getElementById("sendBtn").onclick = sendMessage;

const msgInput = document.getElementById("msgInput");

msgInput.addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});

msgInput.addEventListener("input", () => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;

  if (!isTyping) {
    isTyping = true;
    ws.send(JSON.stringify({ type: "typing", isTyping: true }));
  }

  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(() => {
    isTyping = false;
    ws.send(JSON.stringify({ type: "typing", isTyping: false }));
  }, 800);
});

function sendMessage() {
  const now = Date.now();
  if (now - lastSent < SEND_COOLDOWN) {
    addSystem("You're sending messages too fast.");
    return;
  }

  const text = msgInput.value;
  if (!text.trim()) return;

  ws.send(JSON.stringify({
    type: "chat",
    text
  }));

  addMessage(username, text, true);

  msgInput.value = "";
  lastSent = now;
}

function addMessage(user, text, isMe = false) {
  const div = document.createElement("div");
  div.className = "msg" + (isMe ? " me" : "");

  const timestamp = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });

  div.innerHTML = `
    <div>
      <strong>${user}</strong>
      <span style="font-size:12px;color:#666;">${timestamp}</span>
    </div>
    <div>${text}</div>
  `;

  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function addSystem(text) {
  const div = document.createElement("div");
  div.className = "system";

  const timestamp = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });

  div.textContent = `[${timestamp}] ${text}`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function showTyping(user, state) {
  if (user === username) return;
  typingIndicator.textContent = state ? `${user} is typing...` : "";
}
