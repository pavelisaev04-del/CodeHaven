import os
import re
import shutil
from datetime import datetime
import config


def clean_for_filename(text):
    """
    Убирает символы, недопустимые в именах файлов Windows.
    Оставляет буквы, цифры, пробелы, дефисы, точки.
    """
    if not text:
        return 'Без_названия'
    # Символы, запрещённые в Windows: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/:*?"<>|]', '', text)
    cleaned = cleaned.strip('. ')
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Ограничиваем длину, чтобы путь не был слишком длинным
    return cleaned[:80] if cleaned else 'Без_названия'


def build_filename(date_send, recipient, ext, number=None):
    """
    Формирует имя файла по шаблону:
    ГГГГММДД_Отправка почты Получатель.pdf
    Или с номером: ГГГГММДД_Отправка почты Получатель_2.pdf
    """
    try:
        d = datetime.strptime(date_send, '%d.%m.%Y')
        date_part = d.strftime('%Y%m%d')
    except (ValueError, TypeError):
        date_part = datetime.now().strftime('%Y%m%d')

    recipient_clean = clean_for_filename(recipient) if recipient else 'Получатель'

    if number and number > 1:
        return f'{date_part}_Отправка почты {recipient_clean}_{number}.{ext}'
    return f'{date_part}_Отправка почты {recipient_clean}.{ext}'


def move_receipt_file(temp_path, date_send, recipient, project):
    """
    Переименовывает и перемещает файл чека в папку проекта.

    Структура: STORAGE_FOLDER / Проект / ГГГГММДД_Отправка почты Получатель.pdf

    Возвращает итоговый путь к файлу.
    Исходный файл не удаляется, пока перемещение не завершится успешно.
    """
    if not os.path.exists(temp_path):
        raise FileNotFoundError(f'Временный файл не найден: {temp_path}')

    ext = temp_path.rsplit('.', 1)[-1].lower()

    # Создаём папку проекта
    project_clean = clean_for_filename(project)
    project_folder = os.path.join(config.STORAGE_FOLDER, project_clean)
    os.makedirs(project_folder, exist_ok=True)

    # Подбираем уникальное имя файла
    number = 1
    while True:
        filename = build_filename(date_send, recipient, ext, number if number > 1 else None)
        dest_path = os.path.join(project_folder, filename)
        if not os.path.exists(dest_path):
            break
        number += 1

    # Перемещаем файл только после успешного создания папки
    shutil.move(temp_path, dest_path)

    return dest_path


def cleanup_temp_file(temp_path):
    """Удаляет временный файл, если он существует."""
    try:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
    except OSError:
        pass
