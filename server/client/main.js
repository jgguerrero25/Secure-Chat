// let token = null;
// let ws = null;
// let username = null;

// let lastSent = 0;
// const SEND_COOLDOWN = 1000;

// const loginScreen = document.getElementById("loginScreen");
// const chatScreen = document.getElementById("chatScreen");
// const messages = document.getElementById("messages");
// const onlineList = document.getElementById("onlineList");
// const typingIndicator = document.getElementById("typingIndicator");

// let typingTimeout = null;
// let isTyping = false;

// document.getElementById("loginBtn").onclick = login;

// async function login() {
//   username = document.getElementById("user").value.trim();
//   const password = document.getElementById("pass").value.trim();

//   const res = await fetch("/login", {
//     method: "POST",
//     headers: {"Content-Type": "application/json"},
//     body: JSON.stringify({username, password})
//   });

//   if (!res.ok) {
//     alert("Invalid login");
//     return;
//   }

//   const data = await res.json();
//   token = data.token;

//   loginScreen.style.display = "none";
//   chatScreen.style.display = "flex";

//   connectWS();
// }

// function connectWS() {
//   if (ws) {
//     try { ws.close(); } catch {}
//   }

// ws = new WebSocket(`wss://securechat.onrender.com/ws?token=${token}`);

//   ws.onopen = () => console.log("Connected");

//   ws.onmessage = (event) => {
//     const msg = JSON.parse(event.data);

//     if (msg.type === "online_list") {
//       onlineList.innerHTML = "";
//       msg.data.users.forEach(u => updateOnline(u, true));
//     }

//     if (msg.type === "chat") {
//       const { from, text } = msg.data;
//       addMessage(from, text, from === username);
//     }

//     if (msg.type === "user_joined") {
//       addSystem(`${msg.data.user} joined`);
//       updateOnline(msg.data.user, true);
//     }

//     if (msg.type === "user_left") {
//       addSystem(`${msg.data.user} left`);
//       updateOnline(msg.data.user, false);
//     }

//     if (msg.type === "typing") {
//       showTyping(msg.data.user, msg.data.isTyping);
//     }
//   };

//   ws.onclose = () => {
//     addSystem("Disconnected. Reconnecting...");
//     setTimeout(connectWS, 2000);
//   };
// }

// document.getElementById("sendBtn").onclick = sendMessage;

// const msgInput = document.getElementById("msgInput");

// msgInput.addEventListener("keydown", e => {
//   if (e.key === "Enter") sendMessage();
// });

// msgInput.addEventListener("input", () => {
//   if (!ws || ws.readyState !== WebSocket.OPEN) return;

//   if (!isTyping) {
//     isTyping = true;
//     ws.send(JSON.stringify({ type: "typing", isTyping: true }));
//   }

//   clearTimeout(typingTimeout);
//   typingTimeout = setTimeout(() => {
//     isTyping = false;
//     ws.send(JSON.stringify({ type: "typing", isTyping: false }));
//   }, 800);
// });

// function sendMessage() {
//   const now = Date.now();
//   if (now - lastSent < SEND_COOLDOWN) {
//     addSystem("You're sending messages too fast.");
//     return;
//   }

//   const text = msgInput.value;
//   if (!text.trim()) return;

//   ws.send(JSON.stringify({
//     type: "chat",
//     text
//   }));

//   addMessage(username, text, true);

//   msgInput.value = "";
//   lastSent = now;
// }

// function addMessage(user, text, isMe = false) {
//   const div = document.createElement("div");
//   div.className = "msg" + (isMe ? " me" : "");

//   const timestamp = new Date().toLocaleTimeString([], {
//     hour: "2-digit",
//     minute: "2-digit"
//   });

//   div.innerHTML = `
//     <div>
//       <strong>${user}</strong>
//       <span style="font-size:12px;color:#666;">${timestamp}</span>
//     </div>
//     <div>${text}</div>
//   `;

//   messages.appendChild(div);
//   messages.scrollTop = messages.scrollHeight;
// }

// function addSystem(text) {
//   const div = document.createElement("div");
//   div.className = "system";

//   const timestamp = new Date().toLocaleTimeString([], {
//     hour: "2-digit",
//     minute: "2-digit"
//   });

//   div.textContent = `[${timestamp}] ${text}`;
//   messages.appendChild(div);
//   messages.scrollTop = messages.scrollHeight;
// }

// function updateOnline(user, add) {
//   if (add) {
//     if (document.getElementById(`user-${user}`)) return;
//     const li = document.createElement("li");
//     li.id = `user-${user}`;
//     li.textContent = user;
//     onlineList.appendChild(li);
//   } else {
//     const li = document.getElementById(`user-${user}`);
//     if (li) li.remove();
//   }
// }

// function showTyping(user, state) {
//   if (user === username) return;
//   typingIndicator.textContent = state ? `${user} is typing...` : "";
// }
let ws = null;
let username = null;
let typingTimeout = null;

async function login() {
    username = document.getElementById("username").value;
    let password = document.getElementById("password").value;

    let res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });

    let data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }

    document.getElementById("login").style.display = "none";
    document.getElementById("chat").style.display = "block";

    connectWS(data.token);
}

function connectWS(token) {
    ws = new WebSocket(`wss://${location.host}/ws?token=${token}`);

    ws.onmessage = (event) => {
        let data = JSON.parse(event.data);

        if (data.type === "online") {
            document.getElementById("online").innerText =
                "Online: " + data.users.join(", ");
        }

        if (data.type === "typing") {
            document.getElementById("typing").innerText = `${data.user} is typing...`;
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                document.getElementById("typing").innerText = "";
            }, 1000);
        }

        if (data.type === "message") {
            let msgBox = document.getElementById("messages");
            msgBox.innerHTML += `<div><b>${data.user}:</b> ${data.text}</div>`;
            msgBox.scrollTop = msgBox.scrollHeight;

            ws.send(JSON.stringify({ type: "read" }));
        }
    };
}

function sendTyping() {
    ws.send(JSON.stringify({ type: "typing" }));
}

function sendMessage() {
    let text = document.getElementById("msg").value;
    if (!text.trim()) return;

    ws.send(JSON.stringify({
        type: "message",
        text,
        timestamp: Date.now()
    }));

    document.getElementById("msg").value = "";
}
