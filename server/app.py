import asyncio
import ssl
import time
import json
import os
import hashlib

from aiohttp import web, WSMsgType
import jwt

JWT_SECRET = "CHANGE_ME"
JWT_ALGO = "HS256"
JWT_EXP_SECONDS = 1800
PING_INTERVAL = 20

USERS = {
    "Jonathan Guerrero": "JonathanPass",
    "bob": "bobpass",
    "alice": "alicepass",
}

CONNECTED = {}  # ws -> username

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if username not in USERS or USERS[username] != password:
        return web.json_response({"error": "invalid_credentials"}, status=401)

    token = make_jwt(username)
    return web.json_response({"token": token})


async def broadcast(event, data, exclude=None):
    msg = json.dumps({"type": event, "data": data})
    dead = []

    for ws in list(CONNECTED.keys()):
        if ws is exclude:
            continue
        try:
            await ws.send_str(msg)
        except:
            dead.append(ws)

    for ws in dead:
        CONNECTED.pop(ws, None)


async def upload_file(request):
    # JWT from Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    user = verify_jwt(token)
    if not user:
        return web.Response(status=401, text="Unauthorized")

    reader = await request.multipart()
    field = await reader.next()
    if not field or field.name != "file":
        return web.Response(status=400, text="No file field")

    filename = field.filename
    file_id = os.urandom(16).hex()
    path = os.path.join(UPLOAD_DIR, file_id)

    hasher = hashlib.sha256()
    size = 0

    with open(path, "wb") as f:
        while True:
            chunk = await field.read_chunk()
            if not chunk:
                break
            f.write(chunk)
            hasher.update(chunk)
            size += len(chunk)

    file_hash = hasher.hexdigest()

    return web.json_response({
        "fileId": file_id,
        "filename": filename,
        "size": size,
        "hash": file_hash,
        "from": user,
    })


async def download_file(request):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    user = verify_jwt(token)
    if not user:
        return web.Response(status=401, text="Unauthorized")

    file_id = request.query.get("file_id")
    if not file_id:
        return web.Response(status=400, text="Missing file_id")

    path = os.path.join(UPLOAD_DIR, file_id)
    if not os.path.exists(path):
        return web.Response(status=404, text="Not found")

    # Later: enforce per-file ACLs if you want
    return web.FileResponse(path)


async def websocket_handler(request):
    token = request.query.get("token")
    user = verify_jwt(token)
    if not user:
        return web.Response(status=401, text="Unauthorized")

    ws = web.WebSocketResponse(autoping=False, heartbeat=PING_INTERVAL)
    await ws.prepare(request)

    CONNECTED[ws] = user

    # Send full online list to the new user
    await ws.send_str(json.dumps({
        "type": "online_list",
        "data": {"users": list(set(CONNECTED.values()))}
    }))

    # Broadcast join event only if this is the first connection for this user
    if list(CONNECTED.values()).count(user) == 1:
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
                payload = json.loads(msg.data)
                mtype = payload.get("type")

                if mtype == "typing":
                    await broadcast("typing", {"user": user, "isTyping": payload["isTyping"]}, exclude=ws)
                    continue

                if mtype == "chat":
                    await broadcast("chat", {"from": user, "text": payload["text"]}, exclude=ws)
                    continue

                if mtype == "file":
                    # Broadcast file metadata as a chat event
                    await broadcast("file", {
                        "from": user,
                        "fileId": payload["fileId"],
                        "filename": payload["filename"],
                        "size": payload["size"],
                        "hash": payload["hash"],
                    })
                    continue

    finally:
        old_user = CONNECTED.pop(ws, None)

        if old_user and old_user not in CONNECTED.values():
            await broadcast("user_left", {"user": old_user})

        ping_task.cancel()

    return ws


app = web.Application()

app.router.add_static("/static/", "./client", show_index=True)


async def index(request):
    return web.FileResponse("./client/index.html")


app.router.add_get("/", index)

app.add_routes([
    web.post("/login", login),
    web.get("/ws", websocket_handler),
    web.post("/upload", upload_file),
    web.get("/download", download_file),
])

if __name__ == "__main__":
    sslctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    sslctx.load_cert_chain("certs/fullchain.pem", "certs/privkey.pem")
    web.run_app(app, host="localhost", port=8443, ssl_context=sslctx)
