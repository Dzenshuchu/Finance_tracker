# auth.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QFont


class AuthDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.profile_id = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Finance tracker v1.5")
        self.setFixedSize(450, 300)

        # Основной layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Установка шрифта
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

        # Стиль для меток
        label_style = "QLabel { font-size: 14px; }"

        # Поле логина
        login_layout = QVBoxLayout()
        login_label = QLabel("Логин:")
        login_label.setStyleSheet(label_style)
        login_layout.addWidget(login_label)

        self.login_input = QLineEdit()
        self.login_input.setFixedHeight(35)
        login_layout.addWidget(self.login_input)
        main_layout.addLayout(login_layout)

        # Поле пароля
        password_layout = QVBoxLayout()
        password_label = QLabel("Пароль:")
        password_label.setStyleSheet(label_style)
        password_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setFixedHeight(35)
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.password_input)
        main_layout.addLayout(password_layout)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Стиль для кнопок
        button_style = """
            QPushButton {
                font-size: 14px;
                min-width: 100px;
                min-height: 30px;
                padding: 8px;
            }
        """

        self.login_btn = QPushButton("✅ Войти")
        self.login_btn.setStyleSheet(button_style)
        self.create_btn = QPushButton("Создать профиль")
        self.create_btn.setStyleSheet(button_style)
        self.exit_btn = QPushButton("❌ Выход")
        self.exit_btn.setStyleSheet(button_style)

        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.exit_btn)

        main_layout.addLayout(button_layout)

        # Центрируем кнопки
        button_layout.insertStretch(0, 1)
        button_layout.addStretch(1)

        self.login_btn.clicked.connect(self.handle_login)
        self.create_btn.clicked.connect(self.handle_create)
        self.exit_btn.clicked.connect(self.handle_exit)

        self.setLayout(main_layout)

    def handle_login(self):
        login = self.login_input.text()
        password = self.password_input.text()
        profile_id = self.db.authenticate(login, password)
        if profile_id:
            self.profile_id = profile_id
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")

    def handle_create(self):
        login = self.login_input.text()
        password = self.password_input.text()
        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
        if self.db.create_profile(login, password):
            QMessageBox.information(self, "Успех", "Профиль создан")
            self.handle_login()
        else:
            QMessageBox.warning(self, "Ошибка", "Логин уже существует")

    def handle_exit(self):
        QCoreApplication.instance().quit()