# app_statistics.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
                             QPushButton, QFileDialog, QMessageBox, QDateEdit, QSizePolicy)
from PyQt5.QtCore import Qt, QDate, QDateTime
from PyQt5.QtChart import QChart, QPieSeries, QBarCategoryAxis, QValueAxis, QChartView, QBarSeries, QBarSet
from PyQt5 import QtGui
from PyQt5.QtGui import QFont
import sqlite3
import csv
import openpyxl
from datetime import datetime
from dateutil.relativedelta import relativedelta


class StatisticsTab(QWidget):
    def __init__(self, db, profile_id):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.init_ui()

    def init_ui(self):
        # Основной layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(20)

        # Установка шрифта
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)

        # Панель управления
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        # Увеличиваем размер элементов управления
        control_font = QFont()
        control_font.setPointSize(13)

        # Группа для периода
        period_group = QHBoxLayout()
        period_group.setSpacing(5)
        period_label = QLabel("Период:")
        period_label.setFont(control_font)
        period_group.addWidget(period_label)

        self.period_combo = QComboBox()
        self.period_combo.setFont(control_font)
        self.period_combo.setFixedHeight(35)
        self.period_combo.addItems(["Текущий месяц", "Прошлый месяц", "Год", "Произвольный"])
        self.period_combo.currentTextChanged.connect(
            lambda text: self.update_all())  # Лямбда для игнорирования аргумента
        period_group.addWidget(self.period_combo)

        # Группа для дат
        self.date_group = QHBoxLayout()
        self.date_group.setSpacing(5)
        from_label = QLabel("с")
        from_label.setFont(control_font)
        self.date_group.addWidget(from_label)

        self.date_from = QDateEdit()
        self.date_from.setFont(control_font)
        self.date_from.setFixedHeight(35)
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setVisible(False)
        self.date_from.dateChanged.connect(self.update_all)
        self.date_group.addWidget(self.date_from)

        to_label = QLabel("по")
        to_label.setFont(control_font)
        self.date_group.addWidget(to_label)

        self.date_to = QDateEdit()
        self.date_to.setFont(control_font)
        self.date_to.setFixedHeight(35)
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setVisible(False)
        self.date_to.dateChanged.connect(self.update_all)
        self.date_group.addWidget(self.date_to)

        # Группа для типа данных
        type_group = QHBoxLayout()
        type_group.setSpacing(5)
        type_label = QLabel("Тип данных:")
        type_label.setFont(control_font)
        type_group.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.setFont(control_font)
        self.type_combo.setFixedHeight(35)
        self.type_combo.addItems(["Доходы", "Расходы", "Доходы и Расходы"])
        self.type_combo.currentTextChanged.connect(lambda text: self.update_all())  # Лямбда для игнорирования аргумента
        type_group.addWidget(self.type_combo)

        # Добавляем группы в основной layout
        controls_layout.addLayout(period_group)
        controls_layout.addLayout(self.date_group)
        controls_layout.addStretch(1)
        controls_layout.addLayout(type_group)

        # Кнопки экспорта
        export_group = QHBoxLayout()
        export_group.setSpacing(10)
        self.csv_export_btn = QPushButton("CSV")
        self.csv_export_btn.setFont(control_font)
        self.csv_export_btn.setFixedSize(120, 35)
        self.xlsx_export_btn = QPushButton("XLSX")
        self.xlsx_export_btn.setFont(control_font)
        self.xlsx_export_btn.setFixedSize(120, 35)
        self.csv_export_btn.clicked.connect(lambda: self.export_data("csv"))
        self.xlsx_export_btn.clicked.connect(lambda: self.export_data("xlsx"))
        export_group.addWidget(self.csv_export_btn)
        export_group.addWidget(self.xlsx_export_btn)

        controls_layout.addLayout(export_group)
        main_layout.addLayout(controls_layout)

        # Основная область с метриками и графиками
        content_layout = QHBoxLayout()

        # Левая панель с метриками и кнопками
        left_panel = QVBoxLayout()
        left_panel.setSpacing(20)

        # Метрики
        metrics_widget = QWidget()
        metrics_layout = QVBoxLayout(metrics_widget)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(15)

        self.balance_label = QLabel("💰 Общий баланс: 0 ₽")
        self.balance_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.income_label = QLabel("🟢 Доходы: 0 ₽")
        self.income_label.setStyleSheet("font-size: 16px; color: green;")
        self.expense_label = QLabel("🔴 Расходы: 0 ₽")
        self.expense_label.setStyleSheet("font-size: 16px; color: red;")

        metrics_layout.addWidget(self.balance_label)
        metrics_layout.addWidget(self.income_label)
        metrics_layout.addWidget(self.expense_label)
        metrics_layout.addStretch()

        left_panel.addWidget(metrics_widget)

        # Кнопки переключения графиков
        buttons_widget = QWidget()
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(15)

        self.pie_btn = QPushButton("Круговая")
        self.pie_btn.setFont(control_font)
        self.pie_btn.setFixedHeight(45)
        self.bar_income_expense_btn = QPushButton("Доходы/Расходы")
        self.bar_income_expense_btn.setFont(control_font)
        self.bar_income_expense_btn.setFixedHeight(45)

        self.pie_btn.clicked.connect(self.show_pie_chart)
        self.bar_income_expense_btn.clicked.connect(self.show_bar_chart_income_expense)

        buttons_layout.addWidget(self.pie_btn)
        buttons_layout.addWidget(self.bar_income_expense_btn)
        buttons_layout.addStretch()

        left_panel.addWidget(buttons_widget)
        left_panel.setStretch(0, 1)
        left_panel.setStretch(1, 1)

        content_layout.addLayout(left_panel, stretch=1)

        # График
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        chart_container = QWidget()
        chart_container.setLayout(QVBoxLayout())
        chart_container.layout().setContentsMargins(0, 0, 0, 0)
        chart_container.layout().addWidget(self.chart_view)

        content_layout.addWidget(chart_container, stretch=4)

        main_layout.addLayout(content_layout, stretch=1)

        self.setLayout(main_layout)
        self.update_all()

    def update_all(self):
        try:
            print("update_all called")  # Отладка
            self.update_statistics()
            current_chart = self.chart_view.chart()
            if current_chart and current_chart.title() == "Распределение по категориям":
                self.show_pie_chart()
            elif current_chart and current_chart.title() == "Доходы и расходы по датам":
                self.show_bar_chart_income_expense()

            # Управление видимостью дат для произвольного периода
            period = self.period_combo.currentText()
            is_custom = period == "Произвольный"
            self.date_from.setVisible(is_custom)
            self.date_to.setVisible(is_custom)
        except Exception as e:
            print(f"Ошибка в update_all: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить статистику: {e}")

    def update_statistics(self):
        try:
            period = self.period_combo.currentText()
            query = (
                "SELECT SUM(CASE WHEN [type] = 'Доход' THEN amount ELSE 0 END) as income, "
                "SUM(CASE WHEN [type] = 'Расход' THEN amount ELSE 0 END) as expense "
                "FROM transactions WHERE profile_id = ?"
            )
            params = [self.profile_id]
            today = datetime.now()
            print(f"update_statistics - Today: {today}, Period: {period}")  # Отладка
            if period == "Текущий месяц":
                query += " AND date LIKE ?"
                params.append(f"{today.strftime('%Y-%m')}%")
            elif period == "Прошлый месяц":
                year = today.year
                month = today.month
                if month == 1:
                    year -= 1
                    month = 12
                else:
                    month -= 1
                last_month = today.replace(year=year, month=month)
                print(f"update_statistics - Last month: {last_month}")  # Отладка
                query += " AND date LIKE ?"
                params.append(f"{last_month.strftime('%Y-%m')}%")
            elif period == "Год":
                query += " AND date LIKE ?"
                params.append(f"{today.strftime('%Y')}%")
            elif period == "Произвольный":
                query += " AND date BETWEEN ? AND ?"
                params.extend(
                    [self.date_from.date().toString("yyyy-MM-dd"), self.date_to.date().toString("yyyy-MM-dd")])
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
                print(f"update_statistics - Result: {result}")  # Отладка
                if result:
                    income, expense = result
                    income = float(income or 0)
                    expense = float(expense or 0)
                    balance = income - expense
                    self.balance_label.setText(f"💰 Общий баланс: {balance:.2f} ₽")
                    self.income_label.setText(f"🟢 Доходы: {income:.2f} ₽")
                    self.expense_label.setText(f"🔴 Расходы: {expense:.2f} ₽")
                else:
                    self.balance_label.setText("💰 Общий баланс: 0.00 ₽")
                    self.income_label.setText("🟢 Доходы: 0.00 ₽")
                    self.expense_label.setText("🔴 Расходы: 0.00 ₽")
        except Exception as e:
            print(f"Ошибка в update_statistics: {e}")
            raise  # Передаем ошибку для диагностики

    def show_pie_chart(self):
        try:
            # Сохраняем текущий выбор перед очисткой
            current_type = self.type_combo.currentText()
            if not current_type:
                current_type = "Доходы"  # Значение по умолчанию, если выбор пустой

            # Отключаем сигналы, чтобы избежать рекурсии
            self.type_combo.blockSignals(True)
            self.type_combo.clear()
            self.type_combo.addItems(["Доходы", "Расходы"])
            # Восстанавливаем выбор пользователя
            self.type_combo.setCurrentText(current_type)
            self.type_combo.setEnabled(True)
            self.type_combo.blockSignals(False)

            series = QPieSeries()
            period = self.period_combo.currentText()
            type_filter = self.type_combo.currentText()
            print(f"Pie chart - Period: {period}, Type: {type_filter}")  # Отладка
            query = (
                "SELECT c.name, SUM(t.amount) "
                "FROM transactions t JOIN categories c ON t.category_id = c.id "
                "WHERE t.profile_id = ?"
            )
            params = [self.profile_id]
            today = datetime.now()
            if period == "Текущий месяц":
                query += " AND t.date LIKE ?"
                params.append(f"{today.strftime('%Y-%m')}%")
            elif period == "Прошлый месяц":
                # Вычисляем прошлый месяц вручную
                year = today.year
                month = today.month
                if month == 1:
                    year -= 1
                    month = 12
                else:
                    month -= 1
                last_month = today.replace(year=year, month=month)
                query += " AND t.date LIKE ?"
                params.append(f"{last_month.strftime('%Y-%m')}%")
            elif period == "Год":
                query += " AND t.date LIKE ?"
                params.append(f"{today.strftime('%Y')}%")
            elif period == "Произвольный":
                query += " AND t.date BETWEEN ? AND ?"
                params.extend(
                    [self.date_from.date().toString("yyyy-MM-dd"), self.date_to.date().toString("yyyy-MM-dd")])
            if type_filter == "Доходы":
                query += " AND t.[type] = 'Доход'"
            elif type_filter == "Расходы":
                query += " AND t.[type] = 'Расход'"
            query += " GROUP BY c.id"
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                data = cursor.fetchall()
                print(f"Pie chart data: {data}")  # Отладка
                if not data:
                    QMessageBox.information(self, "Информация", "Нет данных для отображения")
                    return
                total = sum(row[1] for row in data)
                colors = [QtGui.QColor(c) for c in [
                    '#FF6384',  # Розовый
                    '#36A2EB',  # Синий
                    '#FFCE56',  # Желтый
                    '#4BC0C0',  # Бирюзовый
                    '#9966FF',  # Фиолетовый
                    '#FF9F40',  # Оранжевый
                    '#7BE041',  # Зеленый
                    '#FF6F61',  # Коралловый
                    '#6B5B95',  # Темно-фиолетовый
                    '#88B04B',  # Оливковый
                    '#F7CAC9',  # Светло-розовый
                ]]
                for i, (name, amount) in enumerate(data):
                    slice_ = series.append(name, amount)
                    percentage = amount / total * 100
                    if percentage >= 2:
                        slice_.setLabel(f"{name} {percentage:.1f}%")
                        slice_.setLabelVisible(True)
                        slice_.setLabelFont(QFont("Arial", 12))
                    slice_.setColor(colors[i % len(colors)])

            chart = QChart()
            chart.addSeries(series)
            chart.setTitle("Распределение по категориям")
            chart.setTitleFont(QFont("Arial", 16))
            chart.legend().setVisible(True)
            chart.legend().setFont(QFont("Arial", 12))
            chart.setAnimationOptions(QChart.SeriesAnimations)
            self.chart_view.setChart(chart)
        except Exception as e:
            print(f"Ошибка в show_pie_chart: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось отобразить круговую диаграмму: {e}")


    def show_bar_chart_income_expense(self):
        try:
            print("show_bar_chart_income_expense called")  # Отладка
            # Отключаем сигналы, чтобы избежать рекурсии
            self.type_combo.blockSignals(True)
            self.type_combo.clear()
            self.type_combo.addItems(["Доходы и Расходы"])
            self.type_combo.setCurrentText("Доходы и Расходы")
            self.type_combo.setEnabled(False)
            self.type_combo.blockSignals(False)

            period = self.period_combo.currentText()
            query = (
                "SELECT t.date, "
                "SUM(CASE WHEN [type] = 'Доход' THEN amount ELSE 0 END) as income, "
                "SUM(CASE WHEN [type] = 'Расход' THEN amount ELSE 0 END) as expense "
                "FROM transactions t WHERE t.profile_id = ?"
            )
            params = [self.profile_id]
            today = datetime.now()
            print(f"Bar chart - Period: {period}, Profile ID: {self.profile_id}")  # Отладка
            if period == "Текущий месяц":
                query += " AND t.date LIKE ?"
                params.append(f"{today.strftime('%Y-%m')}%")
            elif period == "Прошлый месяц":
                year = today.year
                month = today.month
                if month == 1:
                    year -= 1
                    month = 12
                else:
                    month -= 1
                last_month = today.replace(year=year, month=month)
                query += " AND t.date LIKE ?"
                params.append(f"{last_month.strftime('%Y-%m')}%")
            elif period == "Год":
                query += " AND t.date LIKE ?"
                params.append(f"{today.strftime('%Y')}%")
            elif period == "Произвольный":
                query += " AND t.date BETWEEN ? AND ?"
                params.extend(
                    [self.date_from.date().toString("yyyy-MM-dd"), self.date_to.date().toString("yyyy-MM-dd")])
            query += " GROUP BY t.date ORDER BY t.date"
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                data = cursor.fetchall()
                print(f"Bar chart data: {data}")  # Отладка
                if not data:
                    print("No data returned from query")  # Отладка
                    QMessageBox.information(self, "Информация", "Нет данных для отображения гистограммы")
                    chart = QChart()
                    chart.setTitle("Доходы и расходы по датам")
                    chart.setTitleFont(QFont("Arial", 16))
                    axis_x = QBarCategoryAxis()
                    axis_x.setLabelsFont(QFont("Arial", 10))
                    chart.addAxis(axis_x, Qt.AlignBottom)
                    axis_y = QValueAxis()
                    axis_y.setLabelFormat("%.2f ₽")
                    axis_y.setTitleText("Сумма (₽)")
                    axis_y.setTitleFont(QFont("Arial", 12))
                    axis_y.setRange(0, 1000)
                    axis_y.setLabelsFont(QFont("Arial", 10))
                    chart.addAxis(axis_y, Qt.AlignLeft)
                    self.chart_view.setChart(chart)
                    return

            # Фильтруем данные, исключая даты с нулевыми значениями
            filtered_data = [(d, i, e) for d, i, e in data if i > 0 or e > 0]
            if not filtered_data:
                print("No non-zero data after filtering")  # Отладка
                QMessageBox.information(self, "Информация", "Нет ненулевых данных для отображения")
                return
            dates = [row[0] for row in filtered_data]
            incomes = [float(row[1]) for row in filtered_data]
            expenses = [float(row[2]) for row in filtered_data]
            print(f"Filtered Dates: {dates}, Incomes: {incomes}, Expenses: {expenses}")  # Отладка

            # Форматируем даты для категорий
            categories = [QDateTime.fromString(d, "yyyy-MM-dd").toString("dd.MM") for d in dates]
            print(f"Categories: {categories}")  # Отладка

            # Создаем наборы данных
            income_set = QBarSet("Доходы")
            expense_set = QBarSet("Расходы")
            income_set.setColor(QtGui.QColor("green"))
            expense_set.setColor(QtGui.QColor("red"))
            income_set.append(incomes)
            expense_set.append(expenses)

            # Создаем серию (без накопления)
            series = QBarSeries()
            series.append(income_set)  # Доходы
            series.append(expense_set)  # Расходы
            series.setBarWidth(0.35)
            print(f"Bar series count: {series.count()}")  # Отладка

            # Создаем график
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle("Доходы и расходы по датам")
            chart.setTitleFont(QFont("Arial", 16))
            chart.setAnimationOptions(QChart.SeriesAnimations)

            # Настраиваем ось X (категории)
            axis_x = QBarCategoryAxis()
            axis_x.append(categories)
            axis_x.setLabelsFont(QFont("Arial", 10))
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)
            print(f"Axis X categories: {axis_x.categories()}")  # Отладка

            # Настраиваем ось Y (суммы)
            axis_y = QValueAxis()
            # Пробуем разные шрифты для меток
            label_font = QFont("Arial Unicode MS", 10)  # Пробуем Times New Roman
            axis_y.setLabelsFont(label_font)
            axis_y.setLabelFormat("%.2f ")  # Формат с символом рубля
            axis_y.setTitleText("Сумма (₽)")
            axis_y.setTitleFont(QFont("Arial Unicode MS", 12))
            max_value = max(max(incomes, default=0), max(expenses, default=0)) * 1.2
            axis_y.setRange(0, max_value if max_value > 0 else 1000)
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)
            print(f"Axis Y range: 0 to {axis_y.max()}")  # Отладка
            print(f"Axis Y label format: {axis_y.labelFormat()}")  # Отладка

            # Настраиваем легенду
            chart.legend().setVisible(True)
            chart.legend().setFont(QFont("Arial", 10))
            chart.legend().setAlignment(Qt.AlignBottom)

            # Устанавливаем график
            self.chart_view.setChart(chart)
            self.chart_view.setRenderHint(QtGui.QPainter.Antialiasing)
            print("Chart set to chart_view")  # Отладка
        except Exception as e:
            print(f"Ошибка в show_bar_chart_income_expense: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось отобразить гистограмму: {e}")

    def export_data(self, format_):
        period = self.period_combo.currentText()
        type_filter = self.type_combo.currentText()
        query = (
            "SELECT t.date, c.name, t.[type], t.amount, t.description "
            "FROM transactions t JOIN categories c ON t.category_id = c.id "
            "WHERE t.profile_id = ?"
        )
        params = [self.profile_id]
        today = datetime.now()
        if period == "Текущий месяц":
            query += " AND t.date LIKE ?"
            params.append(f"{today.strftime('%Y-%m')}%")
        elif period == "Прошлый месяц":
            last_month = today - relativedelta(months=1)
            query += " AND t.date LIKE ?"
            params.append(f"{last_month.strftime('%Y-%m')}%")
        elif period == "Год":
            query += " AND t.date LIKE ?"
            params.append(f"{today.strftime('%Y')}%")
        elif period == "Произвольный":
            query += " AND t.date BETWEEN ? AND ?"
            params.extend([self.date_from.date().toString("yyyy-MM-dd"), self.date_to.date().toString("yyyy-MM-dd")])
        if type_filter == "Доходы":
            query += " AND t.[type] = 'Доход'"
        elif type_filter == "Расходы":
            query += " AND t.[type] = 'Расход'"
        # Для "Доходы и Расходы" не добавляем фильтр по типу
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            data = cursor.fetchall()
            if not data:
                QMessageBox.information(self, "Информация", "Нет данных для экспорта")
                return
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if format_ == "csv":
                file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в CSV", f"transactions_{timestamp}.csv",
                                                           "CSV Files (*.csv)")
                if file_path:
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(["Дата", "Категория", "Тип", "Сумма", "Описание"])
                        writer.writerows(data)
                    QMessageBox.information(self, "Успех", "Данные экспортированы в CSV")
            elif format_ == "xlsx":
                file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в XLSX", f"transactions_{timestamp}.xlsx",
                                                           "XLSX Files (*.xlsx)")
                if file_path:
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = "Transactions"
                    ws.append(["Дата", "Категория", "Тип", "Сумма", "Описание"])
                    for row in data:
                        ws.append(row)
                    wb.save(file_path)
                    QMessageBox.information(self, "Успех", "Данные экспортированы в XLSX")