import asyncio
import ssl
import time
import json
from collections import defaultdict

from aiohttp import web, WSMsgType
import jwt
import bcrypt

JWT_SECRET = "CHANGE_ME"
JWT_ALGO = "HS256"
JWT_EXP_SECONDS = 1800
RATE_LIMIT_PER_SEC = 5
RATE_LIMIT_BURST = 10
PING_INTERVAL = 20
MAX_MESSAGE_SIZE = 8000

USERS = {
    "alice": bcrypt.hashpw(b"alicepass", bcrypt.gensalt()).decode(),
    "bob": bcrypt.hashpw(b"bobpass", bcrypt.gensalt()).decode(),
}

CONNECTED = defaultdict(set)

class TokenBucket:
    def __init__(self, rate, burst):
        self.rate = rate
        self.capacity = burst
        self.tokens = burst
        self.last = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, n=1):
        async with self.lock:
            now = time.monotonic()
            delta = now - self.last
            self.last = now
            self.tokens = min(self.capacity, self.tokens + delta * self.rate)
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False

RATE_LIMITERS = defaultdict(lambda: TokenBucket(RATE_LIMIT_PER_SEC, RATE_LIMIT_BURST))

def make_jwt(username):
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + JWT_EXP_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def verify_jwt(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])["sub"]
    except:
        return None

async def login(request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if username not in USERS:
        return web.json_response({"error": "invalid_credentials"}, status=401)

    if not bcrypt.checkpw(password.encode(), USERS[username].encode()):
        return web.json_response({"error": "invalid_credentials"}, status=401)

    token = make_jwt(username)
    return web.json_response({"token": token})

async def broadcast(event, data, exclude=None):
    msg = json.dumps({"type": event, "data": data})
    for user, sockets in CONNECTED.items():
        for ws in list(sockets):
            if ws is exclude:
                continue
            try:
                await ws.send_str(msg)
            except:
                pass

async def websocket_handler(request):
    token = request.query.get("token")
    user = verify_jwt(token)
    if not user:
        return web.Response(status=401, text="Unauthorized")

    ws = web.WebSocketResponse(autoping=False, heartbeat=PING_INTERVAL)
    await ws.prepare(request)

    CONNECTED[user].add(ws)
    await broadcast("user_joined", {"user": user}, exclude=ws)

    async def ping_loop():
        while not ws.closed:
            try:
                await ws.ping()
            except:
                break
            await asyncio.sleep(PING_INTERVAL)

    ping_task = asyncio.create_task(ping_loop())

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if len(msg.data) > MAX_MESSAGE_SIZE:
                    continue

                if not await RATE_LIMITERS[user].consume():
                    await ws.send_str(json.dumps({"type": "error", "data": "rate_limited"}))
                    continue

                payload = json.loads(msg.data)
                if payload.get("type") == "chat":
                    await broadcast("chat", {"from": user, "text": payload.get("text", "")})
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        CONNECTED[user].discard(ws)
        ping_task.cancel()
        await broadcast("user_left", {"user": user})

    return ws

# ---------------------------
# STATIC ROUTES (FIXED)
# ---------------------------

app = web.Application()

# Serve static files under /client/
app.router.add_static("/client/", "./client", show_index=False)

# Serve index.html at root
async def index(request):
    return web.FileResponse("./client/index.html")

app.router.add_get("/", index)

# API routes
app.add_routes([
    web.post("/login", login),
    web.get("/ws", websocket_handler),
])

if __name__ == "__main__":
    sslctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    sslctx.load_cert_chain("certs/fullchain.pem", "certs/privkey.pem")
    web.run_app(app, host="0.0.0.0", port=8443, ssl_context=sslctx)
