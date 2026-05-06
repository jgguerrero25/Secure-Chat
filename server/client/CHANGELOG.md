# Changelog

---

## [3.0.0] - Part 3

### Added
- Cloud hosting via Render (24/7 availability)
- PostgreSQL database on Supabase (persistent user accounts)
- Backblaze B2 cloud file storage (files persist across deploys)
- UptimeRobot monitoring to keep server alive 24/7
- Session persistence — stay logged in on page refresh
- Online/offline presence indicators (green/offline dot in sidebar)
- Logout button with session cleanup
- Active chat user highlight in sidebar
- Chat history saved to localStorage (plaintext log per user pair)
- Client-side file validation (type and size checks before upload)
- Enter key support on login and register forms
- Auto-login after account registration
- Red border validation on login and register forms (no more popups)
- New tab always shows login screen (session only restored on refresh)
- Browser notifications for incoming messages from non-active chats
- Unread message badge on sidebar user when they send you a message
- Admin password reset endpoint (`/reset-password`)
- Expanded emoji picker (40 emojis)
- Messages only delivered when both users have each other selected (no group chat bleed)

### Changed
- Replaced `users.json` local storage with PostgreSQL on Supabase
- File uploads now stored on Backblaze B2 instead of local disk
- JWT expiry extended to 24 hours
- Users stay in sidebar after going offline (shown with grey dot)
- Chat screen now fills full page width
- Users must click a peer before sending messages
- Sidebar only shows users who are actually online

### Fixed
- WebSocket reconnect no longer loops on auth failure
- File download now includes auth token (no more Unauthorized error)
- Message bubble colors correct per user after refresh
- Messages from third users no longer bleed into active chat (group chat issue)
- Emoji picker no longer cut off at bottom of screen

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
- Emoji picker
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