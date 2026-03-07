from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton

class UserSelect(QWidget):
    def __init__(self, on_user_selected):
        super().__init__()
        self.setWindowTitle("Select User")

        layout = QVBoxLayout()

        # Example users — later you load these from your DB
        for user in ["Jonathan", "Bob", "Alice"]:
            btn = QPushButton(user)
            btn.clicked.connect(lambda _, u=user: on_user_selected(u))
            layout.addWidget(btn)

        self.setLayout(layout)
