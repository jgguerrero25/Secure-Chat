## Running SecureChat

1. Open this repository in GitHub.
2. Click "Code" → "Open with Codespaces" → "Create Codespace".
3. Once the Codespace loads, open a terminal.
4. Navigate to the server folder:
   cd server
5. Install dependencies:
   pip install -r requirements.txt
6. Generate TLS certificates (only needed once):
   mkdir certs && openssl req -x509 -newkey rsa:2048 -nodes -keyout certs/privkey.pem -out certs/fullchain.pem -days 365
7. Start the server:
   python app.py
8. When prompted, click "Open in Browser" for port 8443.
9. Login using:
   - alice / alicepass
   - bob / bobpass
