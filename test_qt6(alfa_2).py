import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QComboBox, QTabWidget, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont  # Импортируем QFont

AUTH_DB = "logpasswd.db"


class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.init_db()

    def initUI(self):
        self.setWindowTitle('Окно авторизации')
        self.setGeometry(100, 100, 300, 150)

        layout = QVBoxLayout()
        self.login_label = QLabel('Логин:')
        self.login_input = QLineEdit()
        layout.addWidget(self.login_label)
        layout.addWidget(self.login_input)

        self.password_label = QLabel('Пароль:')
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        buttons_layout = QHBoxLayout()
        self.login_button = QPushButton('Вход')
        self.login_button.clicked.connect(self.on_login)
        buttons_layout.addWidget(self.login_button)

        self.register_button = QPushButton('Регистрация')
        self.register_button.clicked.connect(self.on_register)
        buttons_layout.addWidget(self.register_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def init_db(self):
        """Инициализация базы данных для хранения логинов и паролей."""
        self.conn = sqlite3.connect(AUTH_DB)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                db_path TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def on_login(self):
        """Обработка входа пользователя."""
        login = self.login_input.text()
        password = self.password_input.text()
        if not login or not password:
            QMessageBox.warning(self, 'Ошибка', 'Логин и пароль не могут быть пустыми')
            return

        self.cursor.execute("SELECT password, db_path FROM users WHERE login = ?", (login,))
        result = self.cursor.fetchone()
        if result and result[0] == password:
            db_path = result[1]
            self.db_window = DBWindow(db_path, login)  # Передаем логин
            self.db_window.show()
            self.close()
        else:
            QMessageBox.warning(self, 'Ошибка', 'Неверный логин или пароль')

    def on_register(self):
        """Обработка регистрации нового пользователя."""
        login = self.login_input.text()
        password = self.password_input.text()
        if not login or not password:
            QMessageBox.warning(self, 'Ошибка', 'Логин и пароль не могут быть пустыми')
            return

        # Создаем путь к персональной базе данных
        db_path = f"{login}.db"
        try:
            # Создаем персональную базу данных
            personal_conn = sqlite3.connect(db_path)
            personal_cursor = personal_conn.cursor()
            # Создаем таблицу для профиля
            personal_cursor.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    phone TEXT,
                    full_name TEXT
                )
            """)
            personal_conn.commit()
            personal_conn.close()

            # Добавляем пользователя в основную базу данных
            self.cursor.execute("INSERT INTO users (login, password, db_path) VALUES (?, ?, ?)", (login, password, db_path))
            self.conn.commit()
            QMessageBox.information(self, 'Успех', 'Пользователь успешно зарегистрирован')
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, 'Ошибка', 'Пользователь с таким логином уже существует')


class DBWindow(QWidget):
    def __init__(self, db_path, login):
        super().__init__()
        self.db_path = db_path
        self.login = login  # Сохраняем логин пользователя
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Просмотр базы данных')
        self.setGeometry(100, 100, 600, 400)

        # Создаем вкладки
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_profile_tab(), "Профиль")
        self.tabs.addTab(self.create_database_tab(), "База данных")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def create_profile_tab(self):
        """Создает вкладку для профиля."""
        profile_tab = QWidget()
        layout = QVBoxLayout()

        # Отображение текущего логина
        self.login_label = QLabel(f"Пользователь: {self.login}")
        
        # Изменяем размер текста
        font = QFont("Arial", 19)  # Указываем шрифт и размер
        self.login_label.setFont(font)  # Применяем шрифт к метке
        
        layout.addWidget(self.login_label)

        form_layout = QFormLayout()
        # Поля для ввода данных
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.full_name_input = QLineEdit()
        form_layout.addRow("Email:", self.email_input)
        form_layout.addRow("Номер телефона:", self.phone_input)
        form_layout.addRow("ФИО:", self.full_name_input)

        # Кнопка сохранения
        save_button = QPushButton('Сохранить')
        save_button.clicked.connect(self.save_profile)
        form_layout.addRow(save_button)

        # Загрузка данных профиля
        self.load_profile()

        layout.addLayout(form_layout)
        profile_tab.setLayout(layout)
        return profile_tab

    def create_database_tab(self):
        """Создает вкладку для работы с базой данных."""
        database_tab = QWidget()
        layout = QVBoxLayout()

        # Кнопка для выбора базы данных
        self.load_button = QPushButton('Выбрать и загрузить базу данных')
        self.load_button.clicked.connect(self.select_and_load_db)
        layout.addWidget(self.load_button)

        # Комбобокс для выбора таблиц
        self.table_combobox = QComboBox()
        self.table_combobox.currentIndexChanged.connect(self.on_table_selected)
        layout.addWidget(self.table_combobox)

        # Таблица для отображения данных
        self.table_widget = QTableWidget()
        layout.addWidget(self.table_widget)

        database_tab.setLayout(layout)
        return database_tab

    def load_profile(self):
        """Загружает данные профиля из базы данных."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT email, phone, full_name FROM profile LIMIT 1")
            result = cursor.fetchone()
            if result:
                self.email_input.setText(result[0])
                self.phone_input.setText(result[1])
                self.full_name_input.setText(result[2])
            conn.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при загрузке профиля: {e}')

    def save_profile(self):
        """Сохраняет данные профиля в базу данных."""
        email = self.email_input.text()
        phone = self.phone_input.text()
        full_name = self.full_name_input.text()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM profile")
            cursor.execute("INSERT INTO profile (email, phone, full_name) VALUES (?, ?, ?)", (email, phone, full_name))
            conn.commit()
            conn.close()
            QMessageBox.information(self, 'Успех', 'Данные профиля сохранены')
        except sqlite3.Error as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при сохранении профиля: {e}')

    def select_and_load_db(self):
        """Открывает диалог для выбора базы данных и загружает её."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Выберите базу данных", 
            "", 
            "SQLite Files (*.db);;All Files (*)"
        )
        if file_path:
            self.db_path = file_path
            self.load_db()

    def load_db(self):
        """Загрузка базы данных и отображение списка таблиц."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = self.cursor.fetchall()
            if tables:
                self.table_combobox.clear()
                for table in tables:
                    self.table_combobox.addItem(table[0])
                self.on_table_selected()  # Автоматически выбираем первую таблицу
        except sqlite3.Error as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при загрузке базы данных: {e}')

    def on_table_selected(self):
        """Отображение содержимого выбранной таблицы."""
        table_name = self.table_combobox.currentText()
        if table_name:
            try:
                self.cursor.execute(f"SELECT * FROM {table_name}")
                rows = self.cursor.fetchall()
                columns = [description[0] for description in self.cursor.description]
                self.table_widget.setRowCount(len(rows))
                self.table_widget.setColumnCount(len(columns))
                self.table_widget.setHorizontalHeaderLabels(columns)
                for i, row in enumerate(rows):
                    for j, item in enumerate(row):
                        self.table_widget.setItem(i, j, QTableWidgetItem(str(item)))
            except sqlite3.Error as e:
                QMessageBox.critical(self, 'Ошибка', f'Ошибка при загрузке таблицы: {e}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    auth_window = AuthWindow()
    auth_window.show()
    sys.exit(app.exec())