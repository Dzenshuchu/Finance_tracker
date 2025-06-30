# transactions.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
                             QLineEdit, QDateEdit, QLabel, QMenu, QDialog, QFormLayout, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
import sqlite3

class TransactionsTab(QWidget):
    transaction_updated = pyqtSignal()  # Сигнал для уведомления об изменениях операций

    def __init__(self, db, profile_id):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.table = None
        self.sort_column = -1
        self.sort_order = Qt.AscendingOrder
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self.load_transactions)
        try:
            self.init_ui()
        except Exception as e:
            print(f"Error in init_ui: {str(e)}")
            raise

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Создаём шрифт для элементов управления
        control_font = QFont()
        control_font.setPointSize(14)

        # Создаём промежуточный макет для фильтров и поиска
        filter_search_layout = QVBoxLayout()
        filter_search_layout.setSpacing(10)
        filter_search_layout.setContentsMargins(0, 0, 0, 0)

        # Создаём макет для фильтров (период, тип, категория и т.д.)
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)
        filters_layout.setContentsMargins(0, 0, 0, 0)

        # Период
        period_group = QHBoxLayout()
        period_group.setSpacing(0)
        period_group.setContentsMargins(0, 0, 0, 0)
        period_label = QLabel("Период:")
        period_label.setFont(control_font)
        period_label.setFixedWidth(80)
        period_group.addWidget(period_label)

        self.period_combo = QComboBox()
        self.period_combo.setFont(control_font)
        self.period_combo.setFixedHeight(35)
        self.period_combo.addItems(["Все", "Месяц", "Неделя", "Год", "Произвольный"])
        self.period_combo.currentTextChanged.connect(self.toggle_date_inputs)
        self.period_combo.currentTextChanged.connect(lambda: self.load_timer.start(300))
        period_group.addWidget(self.period_combo)

        filters_layout.addLayout(period_group)

        # Даты
        date_group = QHBoxLayout()
        date_group.setSpacing(5)
        date_group.setContentsMargins(0, 0, 0, 0)

        self.date_from = QDateEdit()
        self.date_from.setFont(control_font)
        self.date_from.setFixedHeight(35)
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setVisible(False)
        self.date_from.dateChanged.connect(lambda: self.load_timer.start(300))
        label_from = QLabel("с")
        label_from.setFont(control_font)
        label_from.setFixedWidth(20)
        date_group.addWidget(label_from)
        date_group.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setFont(control_font)
        self.date_to.setFixedHeight(35)
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setVisible(False)
        self.date_to.dateChanged.connect(lambda: self.load_timer.start(300))
        label_to = QLabel("по")
        label_to.setFont(control_font)
        label_to.setFixedWidth(20)
        date_group.addWidget(label_to)
        date_group.addWidget(self.date_to)

        filters_layout.addLayout(date_group)

        # Тип операции
        type_group = QHBoxLayout()
        type_group.setSpacing(0)
        type_group.setContentsMargins(0, 0, 0, 0)
        type_label = QLabel("Тип:")
        type_label.setFont(control_font)
        type_label.setFixedWidth(50)
        type_group.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.setFont(control_font)
        self.type_combo.setFixedHeight(35)
        self.type_combo.addItems(["Все", "Доход", "Расход"])
        self.type_combo.currentTextChanged.connect(self.update_categories)
        self.type_combo.currentTextChanged.connect(lambda: self.load_timer.start(300))
        type_group.addWidget(self.type_combo)

        filters_layout.addLayout(type_group)

        # Категория
        category_group = QHBoxLayout()
        category_group.setSpacing(0)
        category_group.setContentsMargins(0, 0, 0, 0)
        category_label = QLabel("Категория:")
        category_label.setFont(control_font)
        category_label.setFixedWidth(100)
        category_group.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.setFont(control_font)
        self.category_combo.setFixedHeight(35)
        self.category_combo.currentTextChanged.connect(lambda: self.load_timer.start(300))
        self.update_categories()
        category_group.addWidget(self.category_combo)

        filters_layout.addLayout(category_group)

        # Кнопка "Сброс"
        apply_reset_layout = QHBoxLayout()
        apply_reset_layout.setSpacing(10)
        apply_reset_layout.setContentsMargins(0, 0, 0, 0)

        reset_btn = QPushButton("Сброс")
        reset_btn.setFont(control_font)
        reset_btn.setFixedHeight(35)
        apply_reset_layout.addWidget(reset_btn)

        reset_btn.clicked.connect(self.reset_filters)
        filters_layout.addLayout(apply_reset_layout)

        # Добавляем filters_layout в промежуточный макет
        filter_search_layout.addLayout(filters_layout)

        # Поиск (размещаем ниже фильтров)
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)

        search_label = QLabel("Поиск:")
        search_label.setFont(control_font)
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setFont(control_font)
        self.search_input.setFixedHeight(35)
        self.search_input.textChanged.connect(lambda: self.load_timer.start(300))
        search_layout.addWidget(self.search_input)

        # Добавляем search_layout в промежуточный макет
        filter_search_layout.addLayout(search_layout)

        # Добавляем промежуточный макет в основной макет
        main_layout.addLayout(filter_search_layout)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Дата", "Категория", "Тип", "Сумма", "Описание"])
        print("Table created:", self.table)

        # Увеличение шрифта для таблицы
        table_font = QFont()
        table_font.setPointSize(14)
        self.table.setFont(table_font)
        self.table.horizontalHeader().setFont(table_font)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().sectionClicked.connect(self.handle_sort)

        main_layout.addWidget(self.table)

        # Кнопка добавления операции
        add_btn = QPushButton("Добавить операцию")
        add_btn.setFont(control_font)
        add_btn.setFixedHeight(35)
        add_btn.clicked.connect(self.add_transaction)
        add_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(add_btn)

        self.setLayout(main_layout)

        # Начальная загрузка данных
        self.load_transactions()

    def update_categories(self):
        self.category_combo.clear()
        self.category_combo.addItem("Все")
        type_ = self.type_combo.currentText()
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            if type_ == "Все":
                cursor.execute("SELECT id, name FROM categories WHERE profile_id = ?", (self.profile_id,))
            else:
                cursor.execute(
                    "SELECT id, name FROM categories WHERE profile_id = ? AND type = ?",
                    (self.profile_id, type_)
                )
            for cat_id, name in cursor.fetchall():
                self.category_combo.addItem(name, cat_id)
        # Запускаем обновление через таймер
        self.load_timer.start(300)

    def toggle_date_inputs(self, period):
        is_custom = period == "Произвольный"
        self.date_from.setVisible(is_custom)
        self.date_to.setVisible(is_custom)
        self.load_transactions()

    def reset_filters(self):
        self.period_combo.setCurrentText("Все")
        self.type_combo.setCurrentText("Все")
        self.category_combo.clear()
        self.update_categories()
        self.search_input.clear()
        self.date_from.setVisible(False)
        self.date_to.setVisible(False)
        self.load_transactions()

    def load_transactions(self):
        if not hasattr(self, 'table') or self.table is None:
            print("Error: Table not initialized")
            return

        # Сохраняем текущие параметры сортировки
        sort_column = self.sort_column
        sort_order = self.sort_order

        # Отключаем обновления и сортировку
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)

        # Очищаем таблицу
        self.table.setRowCount(0)

        # Формируем SQL-запрос
        query = """
            SELECT t.id, t.date, c.name, t.type, t.amount, t.description
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.profile_id = ?
        """
        params = [self.profile_id]

        # Фильтры
        if self.type_combo.currentText() != "Все":
            query += " AND t.type = ?"
            params.append(self.type_combo.currentText())

        category_text = self.category_combo.currentText()
        if category_text != "Все":
            category_id = self.category_combo.itemData(self.category_combo.currentIndex())
            if category_id is not None:  # Проверка на валидность category_id
                query += " AND c.id = ?"
                params.append(category_id)

        search_text = self.search_input.text()
        if search_text:
            query += " AND t.description LIKE ?"
            params.append(f"%{search_text}%")

        period = self.period_combo.currentText()
        if period == "Произвольный":
            query += " AND t.date BETWEEN ? AND ?"
            params.extend([self.date_from.date().toString("yyyy-MM-dd"), self.date_to.date().toString("yyyy-MM-dd")])
        elif period == "Месяц":
            query += " AND t.date >= date('now', '-1 month')"
        elif period == "Неделя":
            query += " AND t.date >= date('now', '-7 days')"
        elif period == "Год":
            query += " AND t.date >= date('now', '-1 year')"

        # Добавляем сортировку в SQL
        column_map = {
            0: "t.date",
            1: "c.name",
            2: "t.type",
            3: "t.amount",
            4: "t.description"
        }
        if sort_column in column_map:
            query += f" ORDER BY {column_map[sort_column]} {'ASC' if sort_order == Qt.AscendingOrder else 'DESC'}"

        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                data = cursor.fetchall()
                for row, (id_, date, category, type_, amount, desc) in enumerate(data):
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(str(date) if date else ""))
                    self.table.setItem(row, 1, QTableWidgetItem(str(category) if category else ""))
                    self.table.setItem(row, 2, QTableWidgetItem(str(type_) if type_ else ""))
                    amount_str = f"{amount:+.2f} ₽" if type_ == "Доход" else f"{-amount:.2f} ₽" if amount else "0.00 ₽"
                    amount_item = QTableWidgetItem(amount_str)
                    # Сохраняем числовое значение суммы для корректной сортировки
                    amount_item.setData(Qt.UserRole, float(amount))
                    self.table.setItem(row, 3, amount_item)
                    self.table.setItem(row, 4, QTableWidgetItem(str(desc) if desc else ""))
                    self.table.setRowHeight(row, 40)
                    for col in range(5):
                        self.table.item(row, col).setTextAlignment(Qt.AlignCenter)
                    # Привязываем transaction_id к строке
                    item = self.table.item(row, 0)
                    if item:
                        item.setData(Qt.UserRole, id_)

                header = self.table.horizontalHeader()
                for i in range(self.table.columnCount()):
                    header.setSectionResizeMode(i, header.Stretch)

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка базы данных: {str(e)}")
        finally:
            # Восстанавливаем сортировку и обновления
            self.table.setSortingEnabled(True)
            self.table.setUpdatesEnabled(True)
            if sort_column >= 0:
                self.table.sortItems(sort_column, sort_order)

    def show_context_menu(self, pos):
        menu = QMenu()
        edit_action = menu.addAction("✏️ Редактировать")
        delete_action = menu.addAction("🗑️ Удалить")
        action = menu.exec_(self.table.mapToGlobal(pos))
        row = self.table.currentRow()
        if row < 0:
            return
        # Извлекаем transaction_id из данных ячейки
        transaction_id = self.table.item(row, 0).data(Qt.UserRole)
        if action == edit_action:
            self.edit_transaction(row)
        elif action == delete_action:
            self.delete_transaction(transaction_id)

    def add_transaction(self):
        dialog = TransactionDialog(self.db, self.profile_id)
        if dialog.exec_():
            self.load_transactions()
            self.transaction_updated.emit()  # Вызываем сигнал

    def edit_transaction(self, row):
        transaction_id = self.table.item(row, 0).data(Qt.UserRole)
        if transaction_id is None:
            return
        dialog = TransactionDialog(self.db, self.profile_id, transaction_id)
        if dialog.exec_():
            self.load_transactions()
            self.transaction_updated.emit()  # Вызываем сигнал

    def delete_transaction(self, transaction_id):
        if transaction_id is None:
            return
        if QMessageBox.question(self, "Подтверждение", "Удалить операцию?") == QMessageBox.Yes:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transactions WHERE id = ? AND profile_id = ?",
                               (transaction_id, self.profile_id))
                conn.commit()
            self.load_transactions()
            self.transaction_updated.emit()  # Вызываем сигнал

    def handle_sort(self, logical_index):
        if self.sort_column == logical_index:
            self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self.sort_column = logical_index
            self.sort_order = Qt.AscendingOrder
        self.load_timer.start(300)


class TransactionDialog(QDialog):
    def __init__(self, db, profile_id, transaction_id=None):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.transaction_id = transaction_id
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Добавить операцию" if not self.transaction_id else "Редактировать операцию")
        self.setMinimumSize(500, 350)  # Увеличенный размер окна

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
        control_font.setPointSize(12)

        # Дата
        self.date_input = QDateEdit()
        self.date_input.setFont(control_font)
        self.date_input.setFixedHeight(35)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        layout.addRow("Дата:", self.date_input)

        # Тип операции
        self.type_combo = QComboBox()
        self.type_combo.setFont(control_font)
        self.type_combo.setFixedHeight(35)
        self.type_combo.addItems(["Доход", "Расход"])
        self.type_combo.currentTextChanged.connect(self.update_categories)
        layout.addRow("Тип операции:", self.type_combo)

        # Категория
        self.category_combo = QComboBox()
        self.category_combo.setFont(control_font)
        self.category_combo.setFixedHeight(35)
        self.update_categories()
        layout.addRow("Категория:", self.category_combo)

        # Сумма
        self.amount_input = QLineEdit()
        self.amount_input.setFont(control_font)
        self.amount_input.setFixedHeight(35)
        self.amount_input.setPlaceholderText("Сумма в ₽")
        layout.addRow("Сумма:", self.amount_input)

        # Описание
        self.desc_input = QLineEdit()
        self.desc_input.setFont(control_font)
        self.desc_input.setFixedHeight(35)
        self.desc_input.setPlaceholderText("Описание (необязательно)")
        layout.addRow("Описание:", self.desc_input)

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
        if self.transaction_id:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT date, category_id, type, amount, description "
                    "FROM transactions WHERE id = ? AND profile_id = ?",
                    (self.transaction_id, self.profile_id)
                )
                data = cursor.fetchone()
                if data:
                    date, cat_id, type_, amount, desc = data
                    self.date_input.setDate(QDate.fromString(date, "yyyy-MM-dd"))
                    self.type_combo.setCurrentText(type_)
                    self.update_categories()
                    self.category_combo.setCurrentIndex(self.category_combo.findData(cat_id))
                    self.amount_input.setText(str(amount))
                    self.desc_input.setText(desc or "")

        self.setLayout(layout)

    def update_categories(self):
        self.category_combo.clear()
        type_ = self.type_combo.currentText()
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name FROM categories WHERE profile_id = ? AND type = ?",
                (self.profile_id, type_)
            )
            for cat_id, name in cursor.fetchall():
                self.category_combo.addItem(name, cat_id)

    def save(self):
        try:
            # Проверяем, что поле суммы не пустое и содержит корректное число
            amount_text = self.amount_input.text().strip()
            if not amount_text:
                raise ValueError("Поле 'Сумма' не может быть пустым")

            # Пытаемся преобразовать в число
            try:
                amount = float(amount_text)
            except ValueError:
                raise ValueError("Введите корректное положительное число в поле 'Сумма'")

            # Проверяем, что сумма положительная
            if amount <= 0:
                raise ValueError("Сумма должна быть положительной")

            date = self.date_input.date().toString("yyyy-MM-dd")
            category_id = self.category_combo.itemData(self.category_combo.currentIndex())
            type_ = self.type_combo.currentText()
            description = self.desc_input.text() or None

            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                if self.transaction_id:
                    cursor.execute(
                        "UPDATE transactions SET date = ?, category_id = ?, type = ?, amount = ?, description = ? "
                        "WHERE id = ? AND profile_id = ?",
                        (date, category_id, type_, amount, description, self.transaction_id, self.profile_id)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO transactions (profile_id, date, category_id, type, amount, description) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (self.profile_id, date, category_id, type_, amount, description)
                    )
                conn.commit()
                self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Ошибка базы данных", f"Произошла ошибка: {str(e)}")

