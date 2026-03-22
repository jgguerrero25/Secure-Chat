import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-certificate-errors"
import sys
import json
import urllib.request
import ssl

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl

SERVER = "https://localhost:8443"

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def http_post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{SERVER}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = {}
        try: body = json.loads(e.read())
        except: pass
        return e.code, body


class LoginWindow(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_success = on_login_success
        self.setWindowTitle("SecureChat — Login")
        self.setFixedWidth(300)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>SecureChat</h2>"))

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        layout.addWidget(self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.pass_input)

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.do_login)
        layout.addWidget(login_btn)

        reg_btn = QPushButton("Create Account")
        reg_btn.setStyleSheet("background:#28a745;color:white;")
        reg_btn.clicked.connect(self.do_register)
        layout.addWidget(reg_btn)

        self.setLayout(layout)

    def do_login(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password.")
            return

        status, body = http_post("/login", {"username": username, "password": password})
        if status == 200:
            self.on_success(body["token"], body.get("username", username))
        elif status == 429:
            QMessageBox.critical(self, "Locked Out", "Too many failed attempts. Wait 5 minutes.")
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")

    def do_register(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password.")
            return

        status, body = http_post("/register", {"username": username, "password": password})
        if status == 201:
            QMessageBox.information(self, "Success", "Account created! You can now log in.")
        elif body.get("error") == "username_taken":
            QMessageBox.warning(self, "Error", "Username already taken.")
        else:
            QMessageBox.critical(self, "Error", f"Registration failed ({status}).")


class SecureChatWindow(QMainWindow):
    def __init__(self, token, username, on_switch_user):
        super().__init__()
        self.setWindowTitle("SecureChat")
        self.on_switch_user = on_switch_user

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        switch_btn = QPushButton("Switch User")
        switch_btn.setFixedHeight(32)
        switch_btn.setStyleSheet("background:#e74c3c;color:white;border:none;font-size:13px;")
        switch_btn.clicked.connect(self.switch_user)
        layout.addWidget(switch_btn)

        self.view = QWebEngineView()
        self.view.load(QUrl("https://localhost:8443"))
        # Auto-login once page finishes loading
        self.view.loadFinished.connect(lambda: self.auto_login(token, username))
        layout.addWidget(self.view)

        container.setLayout(layout)
        self.setCentralWidget(container)

    def auto_login(self, token, username):
        js = f"autoLoginFromDesktop('{token}', '{username}');"
        self.view.page().runJavaScript(js)

    def switch_user(self):
        self.view.setUrl(QUrl("about:blank"))

        self.close()
        self.on_switch_user()


class SecureChatApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.token = None
        self.username = None
        self.window = None

        self.login_win = LoginWindow(self.on_login_success)
        self.login_win.show()

    def on_login_success(self, token, username):
        self.token = token
        self.username = username
        self.login_win.hide()
        self.open_chat()

    def open_chat(self):
        self.window = SecureChatWindow(self.token, self.username, on_switch_user=self.show_login)
        self.window.resize(1024, 700)
        self.window.show()

    def show_login(self):
        self.login_win = LoginWindow(self.on_login_success)
        self.login_win.show()

    def run(self):
        sys.exit(self.app.exec())


SecureChatApp().run()