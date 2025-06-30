# main_window.py
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal
from transactions import TransactionsTab
from categories import CategoriesTab
from app_statistics import StatisticsTab
from budget import BudgetTab
from settings import SettingsTab

class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()
    data_updated = pyqtSignal()

    def __init__(self, db, profile_id, login):
        super().__init__()
        self.db = db
        self.profile_id = profile_id
        self.login = login
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Finance tracker v1.5 | {self.login}")
        self.setMinimumSize(1200, 900)
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        header_layout = QHBoxLayout()
        exit_btn = QPushButton("🚪 Выйти")
        exit_btn.clicked.connect(self.logout)
        header_layout.addStretch()
        header_layout.addWidget(exit_btn)
        layout.addLayout(header_layout)
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabBar::tab {
                height: 40px;
                width: 150px;
                font-size: 14pt;  /* Увеличиваем шрифт названий вкладок */
            }
        """)
        self.transactions_tab = TransactionsTab(self.db, self.profile_id)
        self.categories_tab = CategoriesTab(self.db, self.profile_id)
        self.statistics_tab = StatisticsTab(self.db, self.profile_id)
        self.budget_tab = BudgetTab(self.db, self.profile_id)
        self.settings_tab = SettingsTab(self.db, self.profile_id)
        self.categories_tab.category_updated.connect(self.transactions_tab.update_categories)
        self.categories_tab.category_updated.connect(self.transactions_tab.load_transactions)
        self.transactions_tab.transaction_updated.connect(self.data_updated)
        self.data_updated.connect(self.statistics_tab.update_all)
        self.transactions_tab.transaction_updated.connect(self.budget_tab.load_limits)
        tabs.addTab(self.transactions_tab, "Операции")
        tabs.addTab(self.categories_tab, "Категории")
        tabs.addTab(self.statistics_tab, "Статистика")
        tabs.addTab(self.budget_tab, "Бюджет")
        tabs.addTab(self.settings_tab, "Настройки")
        layout.addWidget(tabs)

    def logout(self):
        print("Выход из приложения...")
        self.logout_signal.emit()
        self.close()

    def closeEvent(self, event):
        print("Закрытие окна...")
        event.accept()