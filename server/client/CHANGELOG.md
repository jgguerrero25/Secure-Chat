# Changelog
---

## [2.0.0] - Part 2

### Added
- Desktop GUI using PySide6 (`desktop_app.py`) replacing terminal interface
- User registration system with account creation screen
- Password strength enforcement (uppercase, number, special character required)
- Brute-force login protection (5 attempt lockout for 5 minutes)
- End-to-end encryption using AES-256-GCM and RSA-4096 key exchange
- Session chat logging — new TXT file created per session in `chat_logs/`
- File encryption at rest using AES-256-GCM
- Emoji picker with 20 emojis
- Bold and italic text formatting
- Auto-detected hyperlinks in messages
- DM-based chat — click a user in the sidebar to start a private conversation
- Switch User button to change accounts without restarting the app
- `/register` endpoint for account creation
- `/users` endpoint to list registered users
- `users.json` for persistent user storage with bcrypt-hashed passwords
- `requirements.txt` for easy dependency installation
- User Guide PDF

### Changed
- Login now uses bcrypt password hashing instead of plain-text comparison
- WebSocket handler now routes messages to a specific peer instead of broadcasting to all
- File uploads now encrypted before being saved to disk
- Online user list now clickable to initiate chats
- `CONNECTED` dictionary now tracks peer per connection

### Removed
- Hardcoded plaintext `USERS` dictionary
- Global broadcast for chat messages

---

## [1.0.0] - Part 1

### Added
- WebSocket-based chat server using aiohttp (`app.py`)
- TLS/HTTPS support (WSS) using self-signed certificates
- JWT-based authentication
- Basic login screen via browser
- Online users panel
- Typing indicators
- File upload and download via `/upload` and `/download` endpoints
- SHA-256 file integrity hashing
- Message send cooldown to prevent spam