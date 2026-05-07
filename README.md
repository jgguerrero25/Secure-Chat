# SecureChat

A secure, real-time chat application built for distributed teams. Available as both a **web app** (hosted on Render) and a **desktop app** (PySide6). All messages are end-to-end encrypted using AES-256-GCM and RSA-4096.

---

## Live Version

Access SecureChat online (no installation needed):

**https://secure-chat-1-avp9.onrender.com/**

Just open the link, create an account, and start chatting!

---

## Tech Stack

| Component | Service |
|---|---|
| Backend | Python + aiohttp (hosted on Render) |
| Database | PostgreSQL on Supabase |
| File Storage | Backblaze B2 |
| Uptime Monitoring | UptimeRobot |
| Desktop Client | PySide6 |

---

## Local Setup (Desktop App)

### Requirements

- Python 3.11
- pip
- A virtual environment (venv)
- TLS certificates (see below)

### 1. Clone the Repository

```bash
git clone https://github.com/jgguerrero25/Secure-Chat.git
cd Secure-Chat/server
```

### 2. Create and Activate the Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Generate TLS Certificates (only needed once)

```bash
mkdir certs
openssl req -x509 -newkey rsa:2048 -nodes -keyout certs/privkey.pem -out certs/fullchain.pem -days 365
```

### 5. Start the Server

```bash
python app.py
```

### 6. Launch the Desktop App

Open a second terminal and run:

```bash
python desktop_app.py
```

---

## Usage

1. **Create an Account** — Click "Create Account" and enter a username and password
   - Password must be at least 8 characters, include an uppercase letter, a number, and a special character (e.g. `!@#$%`)
2. **Login** — Enter your credentials and press Enter or click Login
3. **Select a User** — Click a user in the sidebar to start a private encrypted chat
4. **Chat** — Type a message and press Enter or click Send
5. **Logout** — Click the red Logout button to sign out

---

## Features

- End-to-end encryption (AES-256-GCM + RSA-4096)
- Secure user authentication with bcrypt password hashing
- Brute-force login protection (5 attempts → 5 minute lockout)
- Duplicate login prevention (same user can't log in from two tabs)
- Encrypted file transfers stored on Backblaze B2
- Session chat logging (saved as TXT files in `chat_logs/`)
- Emoji picker and text formatting (bold, italic, links)
- Online/offline presence indicators
- Chat history persists on page refresh
- Desktop GUI with user switching
- 24/7 cloud hosting with UptimeRobot monitoring

---

## Project Structure

```
Secure-Chat/
├── CHANGELOG.md
├── README.md
└── server/
    ├── app.py              # Server
    ├── desktop_app.py      # Desktop GUI
    ├── user_select.py      # User selection window
    ├── client/
    │   ├── index.html
    │   └── main.js
    ├── certs/              # TLS certificates (not committed)
    ├── chat_logs/          # Session logs (auto-created)
    ├── uploads/            # Encrypted file uploads (auto-created)
    ├── users.json          # User database fallback (auto-created)
    └── requirements.txt
```

---

## Security Notes

- All passwords are hashed with bcrypt before storage
- Files are encrypted at rest with AES-256-GCM before upload to Backblaze B2
- All traffic is encrypted in transit via TLS (HTTPS/WSS)
- User accounts stored in PostgreSQL on Supabase
- `certs/` is not committed to the repository