# budget.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QComboBox, \
    QLineEdit, QDialog, QFormLayout, QMessageBox, QMenu, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
import sqlite3
from datetime import datetime, timedelta


class BudgetTab(QWidget):
    limit_updated = pyqtSignal()

    def __init__(self, db, profile_id):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self.load_limits)
        self.notified_limits = set()  # Множество для отслеживания лимитов с уведомлениями
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)

        control_font = QFont()
        control_font.setPointSize(12)

        category_label = QLabel("Категория:")
        category_label.setFont(control_font)
        filters_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.setFont(control_font)
        self.category_combo.setFixedHeight(35)
        self.category_combo.addItem("Все")
        self.update_categories()
        self.category_combo.currentTextChanged.connect(self.load_limits)
        filters_layout.addWidget(self.category_combo)

        add_btn = QPushButton("Добавить лимит")
        add_btn.setFont(control_font)
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self.add_limit)
        filters_layout.addStretch()
        filters_layout.addWidget(add_btn)

        layout.addLayout(filters_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Категория", "Лимит", "Остаток", "Период"])

        table_font = QFont()
        table_font.setPointSize(14)
        self.table.setFont(table_font)
        self.table.horizontalHeader().setFont(table_font)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("""
            QTableWidget {
                font-size: 14px;
            }
            QTableWidget::item {
                text-align: center;
                padding: 5px;
            }
            QHeaderView::section {
                font-size: 14px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_limits()

    def update_categories(self):
        self.category_combo.clear()
        self.category_combo.addItem("Все")
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM categories WHERE profile_id = ? AND type = 'Расход'",
                           (self.profile_id,))
            for cat_id, name in cursor.fetchall():
                self.category_combo.addItem(name, cat_id)

    def get_period_range(self, period):
        """Возвращает начальную и конечную даты для периода"""
        today = datetime.now()
        if period == "Неделя":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif period == "Месяц":
            start = today.replace(day=1)
            end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        elif period == "Год":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def load_limits(self):
        self.table.setRowCount(0)
        query = """
            SELECT l.id, c.name, l.amount, l.period 
            FROM limits l 
            JOIN categories c ON l.category_id = c.id 
            WHERE l.profile_id = ?
        """
        params = [self.profile_id]
        category_text = self.category_combo.currentText()
        if category_text != "Все":
            category_id = self.category_combo.itemData(self.category_combo.currentIndex())
            if category_id:
                query += " AND l.category_id = ?"
                params.append(category_id)

        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row, (id_, category, limit_amount, period) in enumerate(cursor.fetchall()):
                start_date, end_date = self.get_period_range(period)
                cursor.execute("""
                    SELECT SUM(amount) 
                    FROM transactions 
                    WHERE profile_id = ? AND category_id = ? AND type = 'Расход' 
                    AND date BETWEEN ? AND ?
                """, (self.profile_id, self.category_combo.itemData(self.category_combo.findText(category)), start_date,
                      end_date))
                spent = cursor.fetchone()[0] or 0
                remaining = limit_amount - spent

                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(category))
                self.table.setItem(row, 1, QTableWidgetItem(f"{limit_amount:.2f} ₽"))
                remaining_item = QTableWidgetItem(f"{remaining:.2f} ₽")
                self.table.setItem(row, 2, remaining_item)
                self.table.setItem(row, 3, QTableWidgetItem(period))

                # Окрашивание ячейки "Остаток"
                used_percentage = (spent / limit_amount * 100) if limit_amount > 0 else 0
                if used_percentage >= 100:
                    remaining_item.setBackground(QColor("#FF5555"))  # Красный
                    # Проверяем, не было ли уже уведомления для этого лимита
                    if id_ not in self.notified_limits and remaining <= 0:
                        QMessageBox.warning(
                            self,
                            "Превышение лимита",
                            f"Лимит для категории '{category}' ({period}) превышен! Остаток: {remaining:.2f} ₽"
                        )
                        self.notified_limits.add(id_)  # Добавляем ID лимита в множество
                elif used_percentage >= 70:
                    remaining_item.setBackground(QColor("#FFFF55"))  # Жёлтый

                self.table.setRowHeight(row, 40)
                for col in range(4):
                    self.table.item(row, col).setTextAlignment(Qt.AlignCenter)
                item = self.table.item(row, 0)
                if item:
                    item.setData(Qt.UserRole, id_)

        header = self.table.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, header.Stretch)

    def update_limits(self):
        self.load_timer.start(300)

    def show_context_menu(self, pos):
        menu = QMenu()
        edit_action = menu.addAction("✏️ Редактировать")
        delete_action = menu.addAction("🗑️ Удалить")
        action = menu.exec_(self.table.mapToGlobal(pos))
        row = self.table.currentRow()
        if row < 0:
            return
        limit_id = self.table.item(row, 0).data(Qt.UserRole)
        if action == edit_action:
            self.edit_limit(row, limit_id)
        elif action == delete_action:
            self.delete_limit(limit_id)

    def add_limit(self):
        dialog = LimitDialog(self.db, self.profile_id)
        if dialog.exec_():
            self.load_limits()
            self.limit_updated.emit()

    def edit_limit(self, row, limit_id):
        dialog = LimitDialog(self.db, self.profile_id, limit_id)
        if dialog.exec_():
            self.load_limits()
            self.limit_updated.emit()

    def delete_limit(self, limit_id):
        if QMessageBox.question(self, "Подтверждение", "Удалить лимит?") == QMessageBox.Yes:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM limits WHERE id = ? AND profile_id = ?", (limit_id, self.profile_id))
                conn.commit()
            self.notified_limits.discard(limit_id)  # Удаляем ID лимита из множества уведомлений
            self.load_limits()
            self.limit_updated.emit()


class LimitDialog(QDialog):
    def __init__(self, db, profile_id, limit_id=None):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.limit_id = limit_id
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Добавить лимит" if not self.limit_id else "Редактировать лимит")
        self.setMinimumSize(400, 250)

        font = QFont()
        font.setPointSize(12)
        self.setFont(font)

        layout = QFormLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)

        control_font = QFont()
        control_font.setPointSize(12)

        self.category_combo = QComboBox()
        self.category_combo.setFont(control_font)
        self.category_combo.setFixedHeight(35)
        self.update_categories()
        layout.addRow("Категория:", self.category_combo)

        self.amount_input = QLineEdit()
        self.amount_input.setFont(control_font)
        self.amount_input.setFixedHeight(35)
        self.amount_input.setPlaceholderText("Сумма лимита в ₽")
        layout.addRow("Лимит:", self.amount_input)

        self.period_combo = QComboBox()
        self.period_combo.setFont(control_font)
        self.period_combo.setFixedHeight(35)
        self.period_combo.addItems(["Неделя", "Месяц", "Год"])
        layout.addRow("Период:", self.period_combo)

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

        if self.limit_id:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT category_id, amount, period FROM limits WHERE id = ? AND profile_id = ?",
                    (self.limit_id, self.profile_id)
                )
                cat_id, amount, period = cursor.fetchone()
                self.category_combo.setCurrentIndex(self.category_combo.findData(cat_id))
                self.amount_input.setText(str(amount))
                self.period_combo.setCurrentText(period or "Месяц")

        self.setLayout(layout)

    def update_categories(self):
        self.category_combo.clear()
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM categories WHERE profile_id = ? AND type = 'Расход'",
                           (self.profile_id,))
            for cat_id, name in cursor.fetchall():
                self.category_combo.addItem(name, cat_id)

    def save(self):
        try:
            amount = float(self.amount_input.text())
            if amount <= 0:
                raise ValueError("Сумма лимита должна быть положительной")
            if amount > 1_000_000:
                raise ValueError("Сумма лимита не должна превышать 1,000,000 ₽")
            category_id = self.category_combo.itemData(self.category_combo.currentIndex())
            period = self.period_combo.currentText()

            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM limits WHERE profile_id = ? AND category_id = ? AND period = ? AND id != ?",
                    (self.profile_id, category_id, period, self.limit_id or 0)
                )
                if cursor.fetchone():
                    raise ValueError("Лимит для этой категории и периода уже существует")

                if self.limit_id:
                    cursor.execute(
                        "UPDATE limits SET category_id = ?, amount = ?, period = ? WHERE id = ? AND profile_id = ?",
                        (category_id, amount, period, self.limit_id, self.profile_id)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO limits (profile_id, category_id, amount, period) VALUES (?, ?, ?, ?)",
                        (self.profile_id, category_id, amount, period)
                    )
                conn.commit()
                self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Ошибка базы данных", f"Произошла ошибка: {str(e)}")