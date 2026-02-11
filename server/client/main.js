// let ws, token, backoff = 1000;

// async function login() {
//   const username = document.getElementById("user").value;
//   const password = document.getElementById("pass").value;

//   const res = await fetch("/login", {
//     method: "POST",
//     headers: {"Content-Type": "application/json"},
//     body: JSON.stringify({username, password})
//   });

//   if (!res.ok) return alert("Login failed");

//   token = (await res.json()).token;
//   connect();
// }

// function connect() {
//   const url = `${location.protocol.replace("http","ws")}//${location.host}/ws?token=${token}`;
//   ws = new WebSocket(url);

//   ws.onopen = () => {
//     backoff = 1000;
//     document.getElementById("chat").style.display = "block";
//   };

//   ws.onmessage = (ev) => {
//     const msg = JSON.parse(ev.data);
//     const div = document.createElement("div");
//     div.textContent = `[${msg.type}] ${JSON.stringify(msg.data)}`;
//     document.getElementById("messages").appendChild(div);
//   };

//   ws.onclose = () => {
//     setTimeout(connect, backoff);
//     backoff = Math.min(backoff * 2, 30000);
//   };
// }

// document.getElementById("loginBtn").onclick = login;
// document.getElementById("sendBtn").onclick = () => {
//   ws.send(JSON.stringify({type:"chat", text:document.getElementById("msg").value}));
// };
// let ws, token, username, backoff = 1000;

// async function login() {
//   username = document.getElementById("user").value;
//   const password = document.getElementById("pass").value;

//   const res = await fetch("/login", {
//     method: "POST",
//     headers: {"Content-Type": "application/json"},
//     body: JSON.stringify({username, password})
//   });

//   if (!res.ok) return alert("Login failed");

//   token = (await res.json()).token;
//   connect();
// }

// function connect() {
//   const url = `${location.protocol.replace("http","ws")}//${location.host}/ws?token=${token}`;
//   ws = new WebSocket(url);

//   ws.onopen = () => {
//     backoff = 1000;
//     document.getElementById("login").style.display = "none";
//     document.getElementById("chat").style.display = "flex";
//   };

//   ws.onmessage = (ev) => {
//     const msg = JSON.parse(ev.data);
//     if (msg.type === "chat") {
//       addMessage(msg.data.from, msg.data.text);
//     }
//     if (msg.type === "user_joined") {
//       addMessage("System", `${msg.data.user} joined`);
//     }
//     if (msg.type === "user_left") {
//       addMessage("System", `${msg.data.user} left`);
//     }
//   };

//   ws.onclose = () => {
//     setTimeout(connect, backoff);
//     backoff = Math.min(backoff * 2, 30000);
//   };
// }

// function addMessage(from, text) {
//   const div = document.createElement("div");
//   div.className = "msg" + (from === username ? " me" : "");
//   div.textContent = `${from}: ${text}`;
//   document.getElementById("messages").appendChild(div);
//   div.scrollIntoView();
// }

// document.getElementById("loginBtn").onclick = login;

// document.getElementById("sendBtn").onclick = () => {
//   const text = document.getElementById("msg").value;
//   ws.send(JSON.stringify({type:"chat", text}));
//   document.getElementById("msg").value = "";
// };
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

  if (!res.ok) return alert("Login failed");

  token = (await res.json()).token;
  connect();
}

function connect() {
  const url = `${location.protocol.replace("http","ws")}//${location.host}/ws?token=${token}`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    backoff = 1000;
    document.getElementById("login").style.display = "none";
    document.getElementById("chat").style.display = "flex";
    document.getElementById("headerName").textContent = `Logged in as ${username}`;
  };

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.type === "chat") {
      addMessage(msg.data.from, msg.data.text);
      if (msg.data.from !== username) audio.play();
    }

    if (msg.type === "user_joined") {
      addSystem(`${msg.data.user} joined`);
      updateUsers();
    }

    if (msg.type === "user_left") {
      addSystem(`${msg.data.user} left`);
      updateUsers();
    }
  };

  ws.onclose = () => {
    setTimeout(connect, backoff);
    backoff = Math.min(backoff * 2, 30000);
  };
}

function addMessage(from, text) {
  const div = document.createElement("div");
  div.className = "msg" + (from === username ? " me" : "");
  div.textContent = `${from === username ? "You" : from}: ${text}`;
  document.getElementById("messages").appendChild(div);
  div.scrollIntoView({behavior: "smooth"});
}

function addSystem(text) {
  const div = document.createElement("div");
  div.className = "system";
  div.textContent = text;
  document.getElementById("messages").appendChild(div);
  div.scrollIntoView({behavior: "smooth"});
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
