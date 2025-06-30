# categories.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QComboBox, \
    QDialog, QFormLayout, QMessageBox, QMenu, QLabel, QLineEdit
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import sqlite3


class CategoriesTab(QWidget):
    category_updated = pyqtSignal()  # Сигнал для уведомления об изменениях категорий

    def __init__(self, db, profile_id):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.init_ui()

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Установка шрифта
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

        # Фильтры
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)

        control_font = QFont()
        control_font.setPointSize(12)

        type_label = QLabel("Тип:")
        type_label.setFont(control_font)
        filters_layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.setFont(control_font)
        self.type_combo.setFixedHeight(35)
        self.type_combo.addItems(["Все", "Доход", "Расход"])
        self.type_combo.currentTextChanged.connect(self.load_categories)
        filters_layout.addWidget(self.type_combo)

        # Кнопка добавления
        add_btn = QPushButton("Добавить категорию")
        add_btn.setFont(control_font)
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self.add_category)
        filters_layout.addStretch()
        filters_layout.addWidget(add_btn)

        layout.addLayout(filters_layout)

        # Таблица категорий
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Название", "Тип"])

        # Увеличение шрифта для таблицы
        table_font = QFont()
        table_font.setPointSize(14)  # Увеличенный шрифт
        self.table.setFont(table_font)
        self.table.horizontalHeader().setFont(table_font)
        self.table.verticalHeader().setDefaultSectionSize(40)  # Увеличенная высота строк
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("""
            QTableWidget {
                font-size: 14px;  // Увеличенный шрифт
            }
            QTableWidget::item {
                text-align: center;
                padding: 5px;
            }
            QHeaderView::section {
                font-size: 14px;  // Увеличенный шрифт для заголовков
                padding: 5px;
            }
        """)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_categories()

    def load_categories(self):
        self.table.setRowCount(0)
        type_ = self.type_combo.currentText()
        query = "SELECT id, name, type FROM categories WHERE profile_id = ?"
        params = [self.profile_id]
        if type_ != "Все":
            query += " AND type = ?"
            params.append(type_)

        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row, (id_, name, type_) in enumerate(cursor.fetchall()):
                self.table.insertRow(row)
                name_item = QTableWidgetItem(name)
                type_item = QTableWidgetItem(type_)
                # Сохраняем category_id в данных ячейки
                name_item.setData(Qt.UserRole, id_)
                self.table.setItem(row, 0, name_item)
                self.table.setItem(row, 1, type_item)
                self.table.setRowHeight(row, 40)  # Увеличенная высота строк
                # Выравнивание по центру
                for col in range(2):
                    self.table.item(row, col).setTextAlignment(Qt.AlignCenter)

        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, header.Stretch)

    def show_context_menu(self, pos):
        menu = QMenu()
        rename_action = menu.addAction("✏️ Переименовать")
        delete_action = menu.addAction("🗑️ Удалить")
        action = menu.exec_(self.table.mapToGlobal(pos))
        row = self.table.currentRow()
        if row < 0:
            return
        # Извлекаем category_id из данных ячейки
        category_id = self.table.item(row, 0).data(Qt.UserRole)
        if action == rename_action:
            self.rename_category(row, category_id)
        elif action == delete_action:
            self.delete_category(category_id)

    def add_category(self):
        dialog = CategoryDialog(self.db, self.profile_id)
        if dialog.exec_():
            self.load_categories()
            self.category_updated.emit()

    def rename_category(self, row, category_id):
        dialog = CategoryDialog(self.db, self.profile_id, category_id)
        if dialog.exec_():
            self.load_categories()  # Обновляем таблицу с сохранением выравнивания
            self.category_updated.emit()

    def delete_category(self, category_id):
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE category_id = ? AND profile_id = ?",
                           (category_id, self.profile_id))
            count = cursor.fetchone()[0]
            if count > 0:
                QMessageBox.warning(self, "Ошибка", "Нельзя удалить категорию, которая используется в операциях")
                return
            if QMessageBox.question(self, "Подтверждение", "Удалить категорию?") == QMessageBox.Yes:
                cursor.execute("DELETE FROM categories WHERE id = ? AND profile_id = ?", (category_id, self.profile_id))
                conn.commit()
                self.load_categories()
                self.category_updated.emit()


class CategoryDialog(QDialog):
    def __init__(self, db, profile_id, category_id=None):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.category_id = category_id
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Добавить категорию" if not self.category_id else "Переименовать категорию")
        self.setMinimumSize(400, 200)

        # Установка шрифта
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

        layout = QFormLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)

        # Увеличиваем элементы формы
        control_font = QFont()
        control_font.setPointSize(14)  # Увеличенный шрифт для диалога

        # Название категории
        self.name_input = QLineEdit()
        self.name_input.setFont(control_font)
        self.name_input.setFixedHeight(35)
        self.name_input.setPlaceholderText("Название категории")
        layout.addRow("Название:", self.name_input)

        # Тип категории
        self.type_combo = QComboBox()
        self.type_combo.setFont(control_font)
        self.type_combo.setFixedHeight(35)
        self.type_combo.addItems(["Доход", "Расход"])
        layout.addRow("Тип:", self.type_combo)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        save_btn = QPushButton("Сохранить")
        save_btn.setFont(control_font)
        save_btn.setFixedHeight(40)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFont(control_font)
        cancel_btn.setFixedHeight(40)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        save_btn.clicked.connect(self.save)
        cancel_btn.clicked.connect(self.reject)

        # Загрузка данных для редактирования
        if self.category_id:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, type FROM categories WHERE id = ? AND profile_id = ?",
                               (self.category_id, self.profile_id))
                name, type_ = cursor.fetchone()
                self.name_input.setText(name)
                self.type_combo.setCurrentText(type_)

        self.setLayout(layout)

    def save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название категории")
            return
        type_ = self.type_combo.currentText()
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            if self.category_id:
                cursor.execute(
                    "UPDATE categories SET name = ?, type = ? WHERE id = ? AND profile_id = ?",
                    (name, type_, self.category_id, self.profile_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO categories (profile_id, name, type) VALUES (?, ?, ?)",
                    (self.profile_id, name, type_)
                )
            conn.commit()
            self.accept()