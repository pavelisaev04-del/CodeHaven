import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Папка для временного хранения загруженных файлов (до подтверждения)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# Папка для постоянного хранения файлов по проектам
# Чтобы изменить — замените путь ниже, например:
# STORAGE_FOLDER = r'D:\Документы\Расходы'
# STORAGE_FOLDER = r'\\server\share\Расходы'
STORAGE_FOLDER = os.path.join(BASE_DIR, 'storage')

# Путь к базе данных SQLite
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'expenses.db')

# Разрешённые форматы файлов
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif'}

# Максимальный размер файла: 32 МБ
MAX_CONTENT_LENGTH = 32 * 1024 * 1024

# Путь к Tesseract OCR (для Windows)
# Скачать: https://github.com/UB-Mannheim/tesseract/wiki
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Секретный ключ Flask (измените для безопасности)
SECRET_KEY = 'mail-expenses-local-secret-2026'

# Хост и порт сервера
# HOST = '0.0.0.0' — доступен из локальной сети
# HOST = '127.0.0.1' — только на этом компьютере
HOST = '0.0.0.0'
PORT = 5000
