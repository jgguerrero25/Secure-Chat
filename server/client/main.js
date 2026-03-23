let token = null;
let ws = null;
let username = null;
let currentPeer = null;
let peerPublicKeys = {};
let myPrivateKey = null;
let myPublicKeyPem = null;      

let lastSent = 0;
const SEND_COOLDOWN = 1000;

const loginScreen = document.getElementById("loginScreen");
const chatScreen = document.getElementById("chatScreen");
const messages = document.getElementById("messages");
const onlineList = document.getElementById("onlineList");
const typingIndicator = document.getElementById("typingIndicator");
const msgInput = document.getElementById("msgInput");
const fileInput = document.getElementById("fileInput");
const emojiBtn = document.getElementById("emojiBtn");
const boldBtn = document.getElementById("boldBtn");
const italicBtn = document.getElementById("italicBtn");

let typingTimeout = null;
let isTyping = false;

// ── NEW: RSA-4096 + AES-256-GCM via WebCrypto ─────────────────────────────────
async function generateKeyPair() {
  const kp = await crypto.subtle.generateKey(
    { name: "RSA-OAEP", modulusLength: 4096,
      publicExponent: new Uint8Array([1,0,1]), hash: "SHA-256" },
    true, ["encrypt", "decrypt"]
  );
  myPrivateKey = kp.privateKey;
  const spki = await crypto.subtle.exportKey("spki", kp.publicKey);
  const b64  = btoa(String.fromCharCode(...new Uint8Array(spki)));
  myPublicKeyPem = `-----BEGIN PUBLIC KEY-----\n${b64.match(/.{1,64}/g).join("\n")}\n-----END PUBLIC KEY-----\n`;
  return myPublicKeyPem;
}

async function importPublicKey(pem) {
  const b64 = pem.replace(/-----[^-]+-----/g, "").replace(/\s/g, "");
  const der  = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  return crypto.subtle.importKey("spki", der.buffer,
    { name: "RSA-OAEP", hash: "SHA-256" }, true, ["encrypt"]);
}

async function encryptMessage(text, recipientKey) {
  const aesKey = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt"]);
  const nonce  = crypto.getRandomValues(new Uint8Array(12));
  const ct     = await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, aesKey, new TextEncoder().encode(text));
  const rawAes = await crypto.subtle.exportKey("raw", aesKey);
  const wrap   = await crypto.subtle.encrypt({ name: "RSA-OAEP" }, recipientKey, rawAes);
  return {
    encrypted:   true,
    ciphertext:  btoa(String.fromCharCode(...new Uint8Array(ct))),
    nonce:       btoa(String.fromCharCode(...nonce)),
    wrapped_key: btoa(String.fromCharCode(...new Uint8Array(wrap))),
  };
}

async function decryptMessage(payload) {
  if (!payload.encrypted) return payload.text || "";
  const b64buf = s => Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer;
  const rawAes = await crypto.subtle.decrypt({ name: "RSA-OAEP" }, myPrivateKey, b64buf(payload.wrapped_key));
  const aesKey = await crypto.subtle.importKey("raw", rawAes, { name: "AES-GCM" }, false, ["decrypt"]);
  const plain  = await crypto.subtle.decrypt({ name: "AES-GCM", iv: b64buf(payload.nonce) }, aesKey, b64buf(payload.ciphertext));
  return new TextDecoder().decode(plain);
}

// ── Screen switching ───────────────────────────────────────────────────────────
const registerScreen = document.getElementById("registerScreen");

document.getElementById("goRegister").onclick = (e) => {
  e.preventDefault();
  loginScreen.style.display    = "none";
  registerScreen.style.display = "flex";
};

document.getElementById("goLogin").onclick = (e) => {
  e.preventDefault();
  registerScreen.style.display = "none";
  loginScreen.style.display    = "flex";
};

// ── Login ──────────────────────────────────────────────────────────────────────
document.getElementById("loginBtn").onclick = async () => {
  username       = document.getElementById("user").value.trim();
  const password = document.getElementById("pass").value.trim();
  if (!username || !password) { alert("Enter username and password."); return; }

  const res = await fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    if (res.status === 429) alert("Too many failed attempts. Wait 5 minutes.");
    else alert("Invalid username or password.");
    return;
  }

  const data = await res.json();
  token    = data.token;
  username = data.username || username;

  await generateKeyPair();

  loginScreen.style.display = "none";
  chatScreen.style.display  = "flex";
  connectWS();
};

// ── Password strength checker ─────────────────────────────────────────────────
function checkPasswordStrength(pass) {
  if (pass.length < 8)               return "Password must be at least 8 characters.";
  if (!/[A-Z]/.test(pass))           return "Password must contain at least one uppercase letter.";
  if (!/[0-9]/.test(pass))           return "Password must contain at least one number.";
  if (!/[!@#$%^&*()_+\-=\[\]{}]/.test(pass)) return "Password must contain at least one special character (!@#$%^&* etc).";
  return null;
}

// ── Register ───────────────────────────────────────────────────────────────────
document.getElementById("registerBtn").onclick = async () => {
  const user  = document.getElementById("regUser").value.trim();
  const pass  = document.getElementById("regPass").value.trim();
  const pass2 = document.getElementById("regPass2").value.trim();

  if (!user || !pass) { alert("Fill in all fields."); return; }
  if (pass !== pass2)  { alert("Passwords do not match."); return; }

  const strengthError = checkPasswordStrength(pass);
  if (strengthError) { alert(strengthError); return; }

  const res = await fetch("/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: user, password: pass }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    if (err.error === "username_taken") alert("Username already taken.");
    else alert("Registration failed.");
    return;
  }

  alert("Account created! You can now log in.");
  registerScreen.style.display = "none";
  loginScreen.style.display    = "flex";
};

// ── Auto-login when called from desktop app ───────────────────────────────────
function autoLoginFromDesktop(tkn, user) {
  token    = tkn;
  username = user;
  loginScreen.style.display    = "none";
  registerScreen.style.display = "none";
  chatScreen.style.display     = "flex";
  generateKeyPair().then(() => connectWS());
}

function connectWS() {
  if (ws) { try { ws.close(); } catch {} }
  ws = new WebSocket(`wss://${location.host}/ws?token=${token}`);
  ws.onopen = () => {
    console.log("Connected");
    ws.send(JSON.stringify({ type: "register_key", public_key: myPublicKeyPem }));
  };

  ws.onmessage = async (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === "session_init") {
      onlineList.innerHTML = "";
      msg.data.users.forEach(u => updateOnline(u, true));
    }

    if (msg.type === "peer_key") {
      peerPublicKeys[msg.data.user] = await importPublicKey(msg.data.public_key);
    }

    if (msg.type === "chat") {
      const { from } = msg.data;
      try {
        const text = await decryptMessage(msg.data);
        addMessage(from, text, false);
      } catch {
        addMessage(from, "[could not decrypt]", false);
      }
    }

    if (msg.type === "user_joined") {
      addSystem(`${msg.data.user} joined`);
      updateOnline(msg.data.user, true);
    }

    if (msg.type === "user_left") {
      addSystem(`${msg.data.user} left`);
      updateOnline(msg.data.user, false);
      delete peerPublicKeys[msg.data.user];
    }

    if (msg.type === "typing") { showTyping(msg.data.user, msg.data.isTyping); }
    if (msg.type === "file")   { addFileMessage(msg.data); }
  };

  ws.onclose = () => {
    addSystem("Disconnected. Reconnecting...");
    setTimeout(connectWS, 2000);
  };
}

// ── Select a peer to chat with ────────────────────────────────────────────────
function selectPeer(peer) {
  currentPeer = peer;
  document.getElementById("topBar").textContent = `SecureChat — ${peer}`;
  messages.innerHTML = "";
  addSystem(`Started encrypted chat with ${peer}`);
  ws.send(JSON.stringify({ type: "select_peer", peer }));
}

document.getElementById("sendBtn").onclick = sendMessage;

msgInput.addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); sendMessage(); }
});

async function sendMessage() {
  const now = Date.now();
  if (now - lastSent < SEND_COOLDOWN) { addSystem("Sending too fast."); return; }
  const text = msgInput.value.trim();
  if (!text || !currentPeer) return;

  const pubKey  = peerPublicKeys[currentPeer];
  const payload = pubKey
    ? await encryptMessage(text, pubKey)
    : { encrypted: false, text };

  ws.send(JSON.stringify({ type: "chat", ...payload }));
  addMessage(username, text, true);
  msgInput.value = "";
  lastSent = now;
}

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

// ── Emoji picker ──────────────────────────────────────────────────────────────
const EMOJIS = ["😀","😂","😍","😎","😭","👍","🔥","❤️","🎉","🤔"];

emojiBtn.addEventListener("click", () => {
  const menu = document.createElement("div");
  menu.style.cssText = "position:absolute;background:white;border:1px solid #ccc;padding:5px;display:flex;flex-wrap:wrap;width:150px;z-index:9999;";
  EMOJIS.forEach(e => {
    const btn = document.createElement("button");
    btn.textContent = e;
    btn.style.cssText = "font-size:20px;margin:3px;cursor:pointer;border:none;background:transparent;";
    btn.onclick = () => { msgInput.value += e; if (document.body.contains(menu)) document.body.removeChild(menu); };
    menu.appendChild(btn);
  });
  const rect = emojiBtn.getBoundingClientRect();
  menu.style.left = rect.left + "px";
  menu.style.top  = rect.bottom + "px";
  document.body.appendChild(menu);
  document.addEventListener("click", function closeMenu(ev) {
    if (!menu.contains(ev.target) && ev.target !== emojiBtn) {
      if (document.body.contains(menu)) document.body.removeChild(menu);
      document.removeEventListener("click", closeMenu);
    }
  });
});

function InsertAroundAtCursor(startTag, endTag) {
  const input = msgInput;
  const start = input.selectionStart, end = input.selectionEnd;
  input.value = input.value.slice(0,start) + startTag + input.value.slice(start,end) + endTag + input.value.slice(end);
  input.focus(); input.setSelectionRange(start + startTag.length, start + startTag.length);
}
boldBtn.addEventListener("click",   () => InsertAroundAtCursor("**", "**"));
italicBtn.addEventListener("click", () => InsertAroundAtCursor("*",  "*"));

// ── File upload ───────────────────────────────────────────────────────────────
fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;
  if (!currentPeer) { alert("Select a user to chat with first."); return; }
  try { await uploadAndSendFile(file); fileInput.value = ""; }
  catch (e) { console.error(e); alert("File upload failed"); }
});

async function uploadAndSendFile(file) {
  if (!token) { alert("Not authenticated"); return; }
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch("/upload", {
    method: "POST", headers: { "Authorization": "Bearer " + token }, body: formData,
  });
  if (!res.ok) throw new Error("Upload failed");
  const info = await res.json();
  ws.send(JSON.stringify({ type: "file", fileId: info.fileId, filename: info.filename,
                            size: info.size, hash: info.hash }));
  addFileMessage({ from: username, ...info });
}

// ── Online users ──────────────────────────────────────────────────────────────
function updateOnline(user, add) {
  if (add) {
    if (document.getElementById(`user-${user}`)) return;
    const li = document.createElement("li");
    li.id = `user-${user}`;
    li.textContent = user;
    li.style.cursor = "pointer";
    li.title = `Chat with ${user}`;
    li.onclick = () => selectPeer(user);
    onlineList.appendChild(li);
  } else {
    const li = document.getElementById(`user-${user}`);
    if (li) li.remove();
  }
}

function formatMessage(text) {
  text = text.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  text = text.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<i>$1</i>");
  text = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
  return text;
}

function addMessage(user, text, isMe = false) {
  const div = document.createElement("div");
  div.className = "msg" + (isMe ? " me" : "");
  const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  div.innerHTML = `<div><strong>${user}</strong><span style="font-size:12px;color:#666;">${ts}</span></div><div>${formatMessage(text)}</div>`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

// ── FIXED: file download with auth token ─────────────────────────────────────
function addFileMessage(data) {
  const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const sizeKb = Math.round(data.size / 1024);

  const msgDiv = document.createElement("div");
  msgDiv.className = "msg";
  msgDiv.innerHTML = `<div><strong>${data.from}</strong><span style="font-size:12px;color:#666;">${ts}</span></div>`;

  const link = document.createElement("a");
  link.href = "#";
  link.textContent = `File: ${data.filename} (${sizeKb} KB)`;
  link.onclick = async (e) => {
    e.preventDefault();
    const res = await fetch(`/download?file_id=${encodeURIComponent(data.fileId)}`, {
      headers: { "Authorization": "Bearer " + token }
    });
    if (!res.ok) { alert("Download failed."); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = data.filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  msgDiv.appendChild(link);
  messages.appendChild(msgDiv);
  messages.scrollTop = messages.scrollHeight;
}

function addSystem(text) {
  const div = document.createElement("div");
  div.className = "system";
  const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  div.textContent = `[${ts}] ${text}`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function showTyping(user, state) {
  if (user === username) return;
  typingIndicator.textContent = state ? `${user} is typing...` : "";
}

// ── Animated background (added by teammate) ───────────────────────────────────
const canvas = document.getElementById("bg");
const ctx = canvas.getContext("2d");
const toggleBtn = document.getElementById("bgToggle");

const MODES = ["particles", "gradient", "matrix"];
let modeIndex = parseInt(localStorage.getItem("bgModeIndex") || "0");
let mode = MODES[modeIndex];

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  canvas.style.position = "fixed";
  canvas.style.top = "0";
  canvas.style.left = "0";
  canvas.style.zIndex = "-1";
  toggleBtn.style.position = "fixed";
  toggleBtn.style.top = "10px";
  toggleBtn.style.right = "10px";
  toggleBtn.style.zIndex = "1000";
  toggleBtn.style.padding = "8px 12px";
}
resize();
window.addEventListener("resize", resize);

let particles = [];
function initParticles() {
  particles = [];
  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 3 + 1,
      dx: Math.random() * 0.5 - 0.25,
      dy: Math.random() * 0.5 - 0.25
    });
  }
}

function drawParticles() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  particles.forEach(p => {
    p.x += p.dx;
    p.y += p.dy;
    if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
    if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0,120,255,0.7)";
    ctx.fill();
  });
}

let t = 0;
function drawGradient() {
  const w = canvas.width, h = canvas.height;
  const gradient = ctx.createLinearGradient(0, 0, w * Math.cos(t * 0.001), h * Math.sin(t * 0.001));
  gradient.addColorStop(0, "#0078ff");
  gradient.addColorStop(0.5, "#00c6ff");
  gradient.addColorStop(1, "#6a11cb");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, w, h);
  t++;
}

const letters = "01";
const fontSize = 14;
let drops = [];

function initMatrix() {
  const columns = Math.floor(canvas.width / fontSize);
  drops = Array(columns).fill(1);
}

function drawMatrix() {
  ctx.fillStyle = "rgba(0,0,0,0.05)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#00ff88";
  ctx.font = fontSize + "px monospace";
  drops.forEach((y, i) => {
    const text = letters[Math.floor(Math.random() * letters.length)];
    ctx.fillText(text, i * fontSize, y * fontSize);
    if (y * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
    drops[i]++;
  });
}

function animate() {
  if (mode === "particles") drawParticles();
  else if (mode === "gradient") drawGradient();
  else if (mode === "matrix") drawMatrix();
  requestAnimationFrame(animate);
}

toggleBtn.onclick = () => {
  modeIndex = (modeIndex + 1) % MODES.length;
  mode = MODES[modeIndex];
  localStorage.setItem("bgModeIndex", modeIndex);
  if (mode === "particles") initParticles();
  if (mode === "matrix") initMatrix();
  updateButton();
};

function updateButton() {
  toggleBtn.textContent = "Mode: " + mode;
}

initParticles();
initMatrix();
updateButton();
animate();