# database.py
import sqlite3
import os
import bcrypt
from datetime import datetime
import shutil


class Database:
    def __init__(self, db_path="db/finance.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Таблица профилей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            """)
            # Таблица категорий
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('Доход', 'Расход')),
                    UNIQUE(profile_id, name),
                    FOREIGN KEY(profile_id) REFERENCES profiles(id)
                )
            """)
            # Таблица операций
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    date TEXT NOT NULL,
                    category_id INTEGER,
                    type TEXT NOT NULL CHECK(type IN ('Доход', 'Расход')),
                    amount REAL NOT NULL,
                    description TEXT,
                    FOREIGN KEY(profile_id) REFERENCES profiles(id),
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )
            """)
            # Таблица лимитов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    category_id INTEGER,
                    amount REAL NOT NULL,
                    period TEXT DEFAULT 'Месяц' CHECK(period IN ('Неделя', 'Месяц', 'Год')),
                    FOREIGN KEY(profile_id) REFERENCES profiles(id),
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )
            """)
            # Проверяем, есть ли столбец period в таблице limits (миграция для существующих баз)
            cursor.execute("PRAGMA table_info(limits)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'period' not in columns:
                cursor.execute("""
                    ALTER TABLE limits ADD COLUMN period TEXT DEFAULT 'Месяц' CHECK(period IN ('Неделя', 'Месяц', 'Год'))
                """)
            conn.commit()

    def create_profile(self, login, password):
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO profiles (login, password) VALUES (?, ?)", (login, hashed))
                conn.commit()
                profile_id = cursor.lastrowid
                # Добавляем базовые категории
                cursor.executemany(
                    "INSERT INTO categories (profile_id, name, type) VALUES (?, ?, ?)",
                    [
                        (profile_id, "Зарплата", "Доход"),
                        (profile_id, "Подработка", "Доход"),
                        (profile_id, "Продукты", "Расход"),
                        (profile_id, "ЖКУ", "Расход"),
                        (profile_id, "Транспорт", "Расход")
                    ]
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def authenticate(self, login, password):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM profiles WHERE login = ?", (login,))
            result = cursor.fetchone()
            if result and bcrypt.checkpw(password.encode('utf-8'), result[1]):
                return result[0]
            return None

    def backup_db(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backups/finance_backup_{timestamp}.db"
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            with sqlite3.connect(backup_path) as backup:
                conn.backup(backup)
        return backup_path

    def restore_db(self, backup_path):
        """
        Восстанавливает базу данных из файла резервной копии.
        Проверяет валидность файла и заменяет текущую базу.
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError("Файл резервной копии не найден")

        # Проверка, является ли файл действительной SQLite-базой
        try:
            with sqlite3.connect(backup_path) as conn:
                cursor = conn.cursor()
                # Проверяем наличие всех необходимых таблиц
                required_tables = ['profiles', 'categories', 'transactions', 'limits']
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                if not all(table in tables for table in required_tables):
                    raise ValueError("Файл резервной копии не содержит всех необходимых таблиц")

                # Проверяем схему таблицы limits на наличие столбца period
                cursor.execute("PRAGMA table_info(limits)")
                columns = [info[1] for info in cursor.fetchall()]
                if 'period' not in columns:
                    raise ValueError("Таблица limits в резервной копии не содержит столбец period")
        except sqlite3.Error as e:
            raise ValueError(f"Недействительный файл SQLite: {str(e)}")

        # Создаем резервную копию текущей базы перед восстановлением
        try:
            temp_backup_path = self.backup_db()
        except Exception as e:
            raise RuntimeError(f"Не удалось создать временную резервную копию: {str(e)}")

        # Закрываем текущее соединение с базой
        self.close()

        # Заменяем текущую базу файлом резервной копии
        try:
            shutil.copyfile(backup_path, self.db_path)
        except Exception as e:
            # Восстанавливаем временную копию в случае ошибки
            shutil.copyfile(temp_backup_path, self.db_path)
            raise RuntimeError(f"Ошибка при копировании файла резервной копии: {str(e)}")

        # Повторно инициализируем базу для проверки целостности
        try:
            self.init_db()
        except Exception as e:
            # Восстанавливаем временную копию в случае ошибки
            shutil.copyfile(temp_backup_path, self.db_path)
            self.init_db()
            raise RuntimeError(f"Ошибка при инициализации восстановленной базы: {str(e)}")

    def close(self):
        # SQLite автоматически закрывает соединение при выходе из контекста,
        # но для явной очистки можно добавить дополнительные действия, если нужно
        pass