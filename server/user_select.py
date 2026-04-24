import json
import urllib.request
import ssl

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QScrollArea, QFrame
from PySide6.QtCore import Qt, QTimer

SERVER = "https://secure-chat-1-avp9.onrender.com/"

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def fetch_users(token):
    req = urllib.request.Request(
        f"{SERVER}/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("users", [])
    except Exception as e:
        print(f"[UserSelect] Could not fetch users: {e}")
        return []


class UserSelect(QWidget):
    def __init__(self, token, current_user, on_user_selected):
        super().__init__()
        self.token = token
        self.current_user = current_user
        self.on_selected = on_user_selected

        self.setWindowTitle("Select Chat Partner")
        self.setMinimumWidth(240)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Logged in as: <b>{current_user}</b>"))
        layout.addWidget(QLabel("Select a user to chat with:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QFrame()
        self.btn_layout = QVBoxLayout(container)
        self.btn_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_users)
        layout.addWidget(refresh_btn)

        self.setLayout(layout)
        self.load_users()

        # Auto-refresh every 5 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_users)
        self.timer.start(5000)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

    def load_users(self):
        users = fetch_users(self.token)
        others = [u for u in users if u != self.current_user]

        # Only update if the list has changed
        current_buttons = [
            self.btn_layout.itemAt(i).widget().text()
            for i in range(self.btn_layout.count())
            if self.btn_layout.itemAt(i).widget() and
               isinstance(self.btn_layout.itemAt(i).widget(), QPushButton)
        ]

        if others == current_buttons:
            return

        while self.btn_layout.count():
            item = self.btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not others:
            self.btn_layout.addWidget(QLabel("No other users found."))
            return

        for user in others:
            btn = QPushButton(user)
            btn.clicked.connect(lambda _, u=user: self.on_selected(u))
            self.btn_layout.addWidget(btn)