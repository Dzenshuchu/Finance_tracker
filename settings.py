# settings.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QDialog, QFormLayout,
    QLineEdit, QMessageBox, QHBoxLayout, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import sqlite3
import bcrypt
import os

class SettingsTab(QWidget):
    def __init__(self, db, profile_id):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Создаем шрифт для кнопок
        button_font = QFont("Arial", 14)

        # Контейнер для кнопок с горизонтальным расположением
        button_container = QWidget()
        button_layout = QHBoxLayout()
        button_container.setLayout(button_layout)
        button_layout.setSpacing(20)

        # Кнопка "Изменить пароль"
        change_password_btn = QPushButton("Изменить пароль")
        change_password_btn.setFont(button_font)
        change_password_btn.setFixedSize(250, 50)
        change_password_btn.clicked.connect(self.change_password)
        button_layout.addWidget(change_password_btn)

        # Кнопка "Создать резервную копию"
        backup_btn = QPushButton("Создать резервную копию")
        backup_btn.setFont(button_font)
        backup_btn.setFixedSize(250, 50)
        backup_btn.clicked.connect(self.create_backup)
        button_layout.addWidget(backup_btn)

        # Кнопка "Восстановить базу данных"
        restore_btn = QPushButton("Восстановить базу данных")
        restore_btn.setFont(button_font)
        restore_btn.setFixedSize(250, 50)
        restore_btn.clicked.connect(self.restore_db)
        button_layout.addWidget(restore_btn)

        # Добавляем растяжки для симметрии
        button_layout.addStretch()
        button_layout.addStretch()

        layout.addWidget(button_container)
        layout.addStretch()
        self.setLayout(layout)

    def change_password(self):
        dialog = ChangePasswordDialog(self.db, self.profile_id)
        dialog.exec_()

    def create_backup(self):
        backup_path = self.db.backup_db()
        QMessageBox.information(self, "Успех", f"Резервная копия создана: {backup_path}")

    def restore_db(self):
        # Диалог для выбора файла резервной копии
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать резервную копию", "backups/",
            "SQLite Database Files (*.db)"
        )
        if not file_path:
            return

        # Подтверждение действия
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Восстановление базы данных перезапишет текущие данные. Продолжить?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        try:
            # Вызываем метод восстановления из класса Database
            self.db.restore_db(file_path)
            QMessageBox.information(self, "Успех", "База данных успешно восстановлена")
            # Сигнализируем об обновлении данных
            from main_window import MainWindow
            if isinstance(self.parent().parent(), MainWindow):
                self.parent().parent().data_updated.emit()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось восстановить базу данных: {str(e)}")

class ChangePasswordDialog(QDialog):
    def __init__(self, db, profile_id):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Изменить пароль")
        layout = QFormLayout()

        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.Password)
        layout.addRow("Старый пароль:", self.old_password_input)

        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        layout.addRow("Новый пароль:", self.new_password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        layout.addRow("Подтвердите новый пароль:", self.confirm_password_input)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        cancel_btn = QPushButton("Отмена")
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        save_btn.clicked.connect(self.save)
        cancel_btn.clicked.connect(self.reject)

        self.setLayout(layout)

    def save(self):
        old_password = self.old_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not old_password or not new_password or not confirm_password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
        if new_password != confirm_password:
            QMessageBox.warning(self, "Ошибка", "Новые пароли не совпадают")
            return

        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM profiles WHERE id = ?", (self.profile_id,))
            stored_password = cursor.fetchone()[0]
            if not bcrypt.checkpw(old_password.encode('utf-8'), stored_password):
                QMessageBox.warning(self, "Ошибка", "Неверный старый пароль")
                return
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("UPDATE profiles SET password = ? WHERE id = ?", (hashed, self.profile_id))
            conn.commit()
            QMessageBox.information(self, "Успех", "Пароль изменён")
            self.accept()