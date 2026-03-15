import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-certificate-errors"
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
from user_select import UserSelect


class SecureChatWindow(QMainWindow):
    def __init__(self, on_switch_user):
        super().__init__()
        self.setWindowTitle("SecureChat")
        self.on_switch_user = on_switch_user

        # Central widget with layout
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Switch User button at the top
        self.switch_btn = QPushButton("Switch User")
        self.switch_btn.setFixedHeight(32)
        self.switch_btn.setStyleSheet("background:#e74c3c;color:white;border:none;font-size:13px;")
        self.switch_btn.clicked.connect(self.switch_user)
        layout.addWidget(self.switch_btn)

        # Web view
        self.view = QWebEngineView()
        self.view.load(QUrl("https://localhost:8443"))
        layout.addWidget(self.view)

        container.setLayout(layout)
        self.setCentralWidget(container)

    def switch_user(self):
        self.close()
        self.on_switch_user()


class SecureChatApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = None
        self.show_selector()

    def show_selector(self):
        self.selector = UserSelect(self.start_chat)
        self.selector.show()

    def start_chat(self, username):
        self.selector.close()
        self.window = SecureChatWindow(on_switch_user=self.show_selector)
        self.window.resize(1024, 700)
        self.window.show()

    def run(self):
        sys.exit(self.app.exec())


SecureChatApp().run()