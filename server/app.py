import os
import json
import asyncio
import bcrypt
import jwt
from aiohttp import web

JWT_SECRET = "supersecret123"
JWT_ALGO = "HS256"

USERS = {
    "jg": bcrypt.hashpw("123".encode(), bcrypt.gensalt()).decode(),
    "friend": bcrypt.hashpw("123".encode(), bcrypt.gensalt()).decode()
}

online_users = set()
sockets = {}

async def login(request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if username not in USERS:
        return web.json_response({"error": "Invalid username"}, status=401)

    if not bcrypt.checkpw(password.encode(), USERS[username].encode()):
        return web.json_response({"error": "Invalid password"}, status=401)

    token = jwt.encode({"username": username}, JWT_SECRET, algorithm=JWT_ALGO)
    return web.json_response({"token": token})

async def websocket_handler(request):
    token = request.query.get("token")
    if not token:
        return web.Response(status=401)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        username = payload["username"]
    except:
        return web.Response(status=401)

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    sockets[username] = ws
    online_users.add(username)

    await broadcast({
        "type": "user_joined",
        "data": {"user": username}
    })

    await broadcast({
        "type": "online_list",
        "data": {"users": list(online_users)}
    })

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            data = json.loads(msg.data)

            if data["type"] == "chat":
                await broadcast({
                    "type": "chat",
                    "data": {"from": username, "text": data["text"]}
                })

            elif data["type"] == "typing":
                await broadcast({
                    "type": "typing",
                    "data": {"user": username, "isTyping": data["isTyping"]}
                })

    # disconnect
    online_users.remove(username)
    del sockets[username]

    await broadcast({
        "type": "user_left",
        "data": {"user": username}
    })

    await broadcast({
        "type": "online_list",
        "data": {"users": list(online_users)}
    })

    return ws

async def broadcast(data):
    dead = []
    for user, ws in sockets.items():
        try:
            await ws.send_json(data)
        except:
            dead.append(user)

    for user in dead:
        del sockets[user]

app = web.Application()
app.router.add_post("/login", login)
app.router.add_get("/ws", websocket_handler)

# IMPORTANT FOR RENDER
app.router.add_static("/", "./server/client", show_index=False)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
