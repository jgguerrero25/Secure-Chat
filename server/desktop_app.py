import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-certificate-errors"
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
from user_select import UserSelect


class SecureChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureChat")

        view = QWebEngineView()
        view.load(QUrl("https://localhost:8443"))
        self.setCentralWidget(view)


class SecureChatApp:
    def __init__(self):
        self.app = QApplication(sys.argv)

        self.selector = UserSelect(self.start_chat)
        self.selector.show()

    def start_chat(self, username):
        self.selector.close()
        self.window = SecureChatWindow()
        self.window.show()

    def run(self):
        sys.exit(self.app.exec())


SecureChatApp().run()
