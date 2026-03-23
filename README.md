# SecureChat

A secure, real-time desktop chat application built for distributed teams. All messages are end-to-end encrypted using AES-256-GCM and RSA-4096. Built with Python, aiohttp, and PySide6.

---

## Requirements

- Python 3.11
- pip
- A virtual environment (venv)
- TLS certificates (see setup below)

---

## Setup

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

---

## Running SecureChat

### Terminal 1 — Start the Server

```bash
python app.py
```

Keep this terminal open. The server runs on `https://localhost:8443`.

### Terminal 2 — Launch the Desktop App

```bash
python desktop_app.py
```

---

## Usage

1. **Create an Account** — Click "Create Account" and enter a username and password.
   - Password must be at least 8 characters, include an uppercase letter, a number, and a special character (e.g. `!@#$%`)
2. **Login** — Enter your credentials and click Login.
3. **Select a User** — Pick a user from the list to start a private encrypted chat.
4. **Chat** — Type a message and press Enter or click Send.
5. **Switch User** — Click the red "Switch User" button at the top to log in as someone else.

---

## Features

- End-to-end encryption (AES-256-GCM + RSA-4096)
- Secure user authentication with bcrypt password hashing
- Brute-force login protection (5 attempts → 5 minute lockout)
- Encrypted file transfers
- Session chat logging (saved as TXT files in `chat_logs/`)
- Emoji picker and text formatting (bold, italic, links)
- Desktop GUI with user switching
- Auto-refreshing user list

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
    ├── users.json          # User database (auto-created)
    └── requirements.txt
```

---

## Security Notes

- `users.json` and `certs/` are not committed to the repository.
- All passwords are hashed with bcrypt before storage.
- Files are encrypted at rest with AES-256-GCM.
- All traffic is encrypted in transit via TLS (HTTPS/WSS).