let ws, token, username, backoff = 1000;
let typingTimeout;
let audio = new Audio("/client/notify.mp3"); // optional sound file

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

  ws.onopen = () => console.log("Connected");

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === "chat") {
      addMessage(msg.data.from, msg.data.text);
    }

    if (msg.type === "user_joined") {
      addSystem(`${msg.data.user} joined`);
      updateOnline(msg.data.user, true);
    }

    if (msg.type === "user_left") {
      addSystem(`${msg.data.user} left`);
      updateOnline(msg.data.user, false);
    }
  };

  ws.onclose = () => {
    addSystem("Disconnected. Reconnecting...");
    setTimeout(connectWS, 2000);
  };
}

document.getElementById("sendBtn").onclick = sendMessage;
document.getElementById("msgInput").addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});

function sendMessage() {
  const now = Date.now();
  if (now - lastSent < SEND_COOLDOWN) {
    addSystem("You're sending messages too fast. Slow down.");
    return;
  }

  const text = document.getElementById("msgInput").value;
  if (!text.trim()) return;

  ws.send(JSON.stringify({text}));
  addMessage(username, text, true);

  document.getElementById("msgInput").value = "";
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
    <strong>${user}</strong>
    <span style="font-size:12px;color:#666;">${timestamp}</span><br>
    ${text}
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

function updateUsers() {
  // You can enhance this later by tracking CONNECTED users from server
}

document.getElementById("loginBtn").onclick = login;

document.getElementById("sendBtn").onclick = sendMessage;

document.getElementById("msg").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});

function sendMessage() {
  const text = document.getElementById("msg").value.trim();
  if (!text) return;

  ws.send(JSON.stringify({type:"chat", text}));
  document.getElementById("msg").value = "";
}
