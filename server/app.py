import asyncio
import ssl
import time
import json
import os
import hashlib
import base64
import re
from datetime import datetime
from collections import defaultdict

from aiohttp import web, WSMsgType
import jwt
import bcrypt
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

JWT_SECRET = "CHANGE_ME"
JWT_ALGO = "HS256"
JWT_EXP_SECONDS = 1800
PING_INTERVAL = 20

UPLOAD_DIR = "uploads"
LOGS_DIR   = "chat_logs"
USERS_FILE = "users.json"

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS    = 300

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOGS_DIR,   exist_ok=True)

CONNECTED      = {}   
LOGIN_ATTEMPTS = defaultdict(lambda: {"count": 0, "locked_until": 0})
USER_KEYS      = {}   
FILE_META      = {}  
SESSION_LOGS   = {}   

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE) as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def make_jwt(username):
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + JWT_EXP_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def verify_jwt(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])["sub"]
    except:
        return None

def is_locked(key):
    return LOGIN_ATTEMPTS[key]["locked_until"] > time.time()

def record_fail(key):
    r = LOGIN_ATTEMPTS[key]
    r["count"] += 1
    if r["count"] >= MAX_LOGIN_ATTEMPTS:
        r["locked_until"] = time.time() + LOCKOUT_SECONDS
        r["count"] = 0

def reset_attempts(key):
    LOGIN_ATTEMPTS[key] = {"count": 0, "locked_until": 0}

# ── Session logging ────────────────────────────────────────────────────────────
def open_log(user_a, user_b):
    key = tuple(sorted([user_a, user_b]))
    if key not in SESSION_LOGS:
        folder = os.path.join(LOGS_DIR, "_".join(key))
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        f = open(os.path.join(folder, f"{stamp}.txt"), "a", encoding="utf-8")
        f.write(f"=== Session opened {datetime.now().isoformat()} ===\n")
        f.flush()
        SESSION_LOGS[key] = f
    return SESSION_LOGS[key]

def log_msg(sender, recipient, text):
    f = open_log(sender, recipient)
    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {sender} -> {recipient}: {text}\n")
    f.flush()

def close_log(user_a, user_b):
    key = tuple(sorted([user_a, user_b]))
    if key in SESSION_LOGS:
        SESSION_LOGS[key].write(f"=== Session closed {datetime.now().isoformat()} ===\n")
        SESSION_LOGS[key].close()
        del SESSION_LOGS[key]

# ── E2E encryption (RSA-4096 + AES-256-GCM) ───────────────────────────────────
def gen_keypair(username):
    priv = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    USER_KEYS[username] = {"private": priv, "public_pem": pub_pem}
    return pub_pem

def encrypt_msg(recipient, plaintext):
    if recipient not in USER_KEYS:
        return {"encrypted": False, "text": plaintext}
    pub     = USER_KEYS[recipient]["private"].public_key()
    aes_key = os.urandom(32)
    nonce   = os.urandom(12)
    ct      = AESGCM(aes_key).encrypt(nonce, plaintext.encode(), None)
    wrapped = pub.encrypt(aes_key, padding.OAEP(
        mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None
    ))
    return {
        "encrypted":   True,
        "ciphertext":  base64.b64encode(ct).decode(),
        "nonce":       base64.b64encode(nonce).decode(),
        "wrapped_key": base64.b64encode(wrapped).decode(),
    }

def decrypt_msg(recipient, payload):
    if not payload.get("encrypted"):
        return payload.get("text", "")
    priv    = USER_KEYS[recipient]["private"]
    aes_key = priv.decrypt(base64.b64decode(payload["wrapped_key"]),
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    return AESGCM(aes_key).decrypt(
        base64.b64decode(payload["nonce"]), base64.b64decode(payload["ciphertext"]), None
    ).decode()

def encrypt_file(src, dst):
    key, nonce = os.urandom(32), os.urandom(12)
    with open(src, "rb") as f: data = f.read()
    with open(dst, "wb") as f: f.write(AESGCM(key).encrypt(nonce, data, None))
    return base64.b64encode(nonce + key).decode()

def decrypt_file(path, key_tag):
    raw = base64.b64decode(key_tag)
    with open(path, "rb") as f: ct = f.read()
    return AESGCM(raw[12:]).decrypt(raw[:12], ct, None)

async def register(request):
    data     = await request.json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return web.json_response({"error": "missing_fields"}, status=400)

    # Password strength validation
    if len(password) < 8:
        return web.json_response({"error": "password_too_short"}, status=400)
    if not re.search(r'[A-Z]', password):
        return web.json_response({"error": "password_no_uppercase"}, status=400)
    if not re.search(r'[0-9]', password):
        return web.json_response({"error": "password_no_number"}, status=400)
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{}]', password):
        return web.json_response({"error": "password_no_special"}, status=400)
    users = load_users()
    if username in users:
        return web.json_response({"error": "username_taken"}, status=409)
    users[username] = {"password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()}
    save_users(users)
    return web.json_response({"ok": True}, status=201)

async def login(request):
    data     = await request.json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    ip       = request.remote or "unknown"

    for key in (ip, username):
        if is_locked(key):
            return web.json_response({"error": "too_many_attempts"}, status=429)

    users  = load_users()
    record = users.get(username)
    if not record or not bcrypt.checkpw(password.encode(), record["password_hash"].encode()):
        for key in (ip, username): record_fail(key)
        return web.json_response({"error": "invalid_credentials"}, status=401)

    reset_attempts(ip); reset_attempts(username)
    return web.json_response({"token": make_jwt(username), "username": username})

async def get_users(request):
    auth = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not verify_jwt(auth):
        return web.Response(status=401)
    return web.json_response({"users": list(load_users().keys())})

async def broadcast(event, data, exclude=None):
    msg  = json.dumps({"type": event, "data": data})
    dead = []
    for ws in list(CONNECTED.keys()):
        if ws is exclude: continue
        try:    await ws.send_str(msg)
        except: dead.append(ws)
    for ws in dead: CONNECTED.pop(ws, None)

async def send_to(username, event, data):
    msg  = json.dumps({"type": event, "data": data})
    dead = []
    for ws, info in list(CONNECTED.items()):
        if info["user"] == username:
            try:    await ws.send_str(msg)
            except: dead.append(ws)
    for ws in dead: CONNECTED.pop(ws, None)

async def upload_file(request):
    auth = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = verify_jwt(auth)
    if not user:
        return web.Response(status=401, text="Unauthorized")

    reader = await request.multipart()
    field  = await reader.next()
    if not field or field.name != "file":
        return web.Response(status=400, text="No file field")

    filename = field.filename
    file_id  = os.urandom(16).hex()
    tmp = os.path.join(UPLOAD_DIR, file_id + ".tmp")
    enc = os.path.join(UPLOAD_DIR, file_id)

    hasher, size = hashlib.sha256(), 0
    with open(tmp, "wb") as f:
        while True:
            chunk = await field.read_chunk()
            if not chunk: break
            f.write(chunk); hasher.update(chunk); size += len(chunk)

    key_tag = encrypt_file(tmp, enc)
    os.unlink(tmp)
    FILE_META[file_id] = {"filename": filename, "size": size,
                          "hash": hasher.hexdigest(), "key_tag": key_tag}
    return web.json_response({"fileId": file_id, "filename": filename,
                               "size": size, "hash": hasher.hexdigest(), "from": user})

# ── UPDATED: download_file — decrypts on the fly ─────────────────────────────
async def download_file(request):
    auth = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not verify_jwt(auth):
        return web.Response(status=401, text="Unauthorized")

    file_id = request.query.get("file_id", "")
    if not file_id or "/" in file_id or ".." in file_id:
        return web.Response(status=400, text="Bad file_id")

    meta = FILE_META.get(file_id)
    path = os.path.join(UPLOAD_DIR, file_id)
    if not meta or not os.path.exists(path):
        return web.Response(status=404, text="Not found")

    return web.Response(
        body=decrypt_file(path, meta["key_tag"]),
        content_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{meta["filename"]}"'},
    )

# ── UPDATED: websocket_handler — DMs, peer selection, E2E keys, logging ──────
async def websocket_handler(request):
    token = request.query.get("token")
    user  = verify_jwt(token)
    if not user:
        return web.Response(status=401, text="Unauthorized")

    ws = web.WebSocketResponse(autoping=False, heartbeat=PING_INTERVAL)
    await ws.prepare(request)

    CONNECTED[ws] = {"user": user, "peer": None}

    # Send online list to the new user
    await ws.send_str(json.dumps({
        "type": "session_init",
        "data": {
            "users": list(set(i["user"] for i in CONNECTED.values())),
        }
    }))

    if [i["user"] for i in CONNECTED.values()].count(user) == 1:
        await broadcast("user_joined", {"user": user}, exclude=ws)

    async def ping_loop():
        while not ws.closed:
            try:    await ws.ping()
            except: break
            await asyncio.sleep(PING_INTERVAL)

    ping_task = asyncio.create_task(ping_loop())

    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT: continue
            payload = json.loads(msg.data)
            mtype   = payload.get("type")

            if mtype == "register_key":
                # Client sends us their browser-generated public key to store
                USER_KEYS[user] = {"public_pem": payload.get("public_key", "").encode()}

            elif mtype == "typing":
                peer = CONNECTED[ws].get("peer")
                if peer:
                    await send_to(peer, "typing", {"user": user, "isTyping": payload["isTyping"]})

            elif mtype == "select_peer":
                old = CONNECTED[ws].get("peer")
                if old: close_log(user, old)
                new_peer = payload.get("peer")
                CONNECTED[ws]["peer"] = new_peer
                if new_peer:
                    open_log(user, new_peer)
                    if new_peer in USER_KEYS:
                        await ws.send_str(json.dumps({
                            "type": "peer_key",
                            "data": {"user": new_peer,
                                     "public_key": USER_KEYS[new_peer]["public_pem"].decode()}
                        }))
                    # Also notify the peer that we want to chat (so they can send us their key)
                    if new_peer in [i["user"] for i in CONNECTED.values()]:
                        if user in USER_KEYS:
                            await send_to(new_peer, "peer_key", {
                                "user": user,
                                "public_key": USER_KEYS[user]["public_pem"].decode()
                            })

            elif mtype == "chat":
                peer = CONNECTED[ws].get("peer")
                if not peer: continue
                text = payload.get("text", "[encrypted]")
                log_msg(user, peer, text)
                await send_to(peer, "chat", {"from": user, **{k: v for k, v in payload.items() if k != "type"}})

            elif mtype == "file":
                peer = CONNECTED[ws].get("peer")
                if not peer: continue
                log_msg(user, peer, f"[file] {payload.get('filename', '')}")
                await send_to(peer, "file", {
                    "from": user, "fileId": payload["fileId"],
                    "filename": payload["filename"], "size": payload["size"],
                    "hash": payload["hash"],
                })

    finally:
        info = CONNECTED.pop(ws, None)
        if info:
            if info.get("peer"): close_log(info["user"], info["peer"])
            if info["user"] not in [i["user"] for i in CONNECTED.values()]:
                await broadcast("user_left", {"user": info["user"]})
                USER_KEYS.pop(info["user"], None)
        ping_task.cancel()

    return ws

# ── App setup (same as original + /register and /users) ───────────────────────
app = web.Application()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(BASE_DIR, "client")

app.router.add_static("/static/", CLIENT_DIR, show_index=True)

async def index(request):
    return web.FileResponse(os.path.join(CLIENT_DIR, "index.html"))

app.router.add_get("/", index)
app.add_routes([
    web.post("/register", register),
    web.post("/login",    login),
    web.get("/users",     get_users),
    web.get("/ws",        websocket_handler),
    web.post("/upload",   upload_file),
    web.get("/download",  download_file),
])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8443))
    
    # Use SSL only if certs exist (local dev), otherwise let Render handle it
    cert = "certs/fullchain.pem"
    key  = "certs/privkey.pem"
    
    if os.path.exists(cert) and os.path.exists(key):
        sslctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        sslctx.load_cert_chain(cert, key)
        web.run_app(app, host="0.0.0.0", port=port, ssl_context=sslctx)
    else:
        web.run_app(app, host="0.0.0.0", port=port)