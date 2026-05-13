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


def get_project_folder(project):
    """
    Возвращает путь к папке проекта на сервере.

    Структура пути:
        STORAGE_BASE \ [Название проекта] \ STORAGE_EXPENSES_SUBFOLDER

    Пример:
        R:\149. БЛИНОВСКАЯ\10. Расходы
        R:\158. ГОНЧАРОВА\10. Расходы
        R:\117. ЛЕОНИДАС\10. Расходы

    «Название проекта» в форме должно совпадать с именем папки на диске R:.
    """
    base = getattr(config, 'STORAGE_BASE', None) or getattr(config, 'STORAGE_FOLDER', '.')
    subfolder = getattr(config, 'STORAGE_EXPENSES_SUBFOLDER', '')

    # Название проекта используем как есть (не очищаем точки и цифры —
    # они нужны, т.к. папки на R: называются "149. БЛИНОВСКАЯ")
    project_name = project.strip() if project else 'Без_проекта'

    if subfolder:
        return os.path.join(base, project_name, subfolder)
    return os.path.join(base, project_name)


def move_receipt_file(temp_path, date_send, recipient, project):
    """
    Переименовывает и перемещает файл чека в папку проекта на сервере.

    Итоговый путь:
        R:\[Название проекта]\10. Расходы\ГГГГММДД_Отправка почты Получатель.pdf

    Возвращает итоговый путь к файлу.
    Исходный файл не удаляется, пока перемещение не завершится успешно.
    """
    if not os.path.exists(temp_path):
        raise FileNotFoundError(f'Временный файл не найден: {temp_path}')

    ext = temp_path.rsplit('.', 1)[-1].lower()

    # Определяем и создаём папку проекта
    project_folder = get_project_folder(project)
    try:
        os.makedirs(project_folder, exist_ok=True)
    except OSError as e:
        raise OSError(
            f'Не удалось создать папку: {project_folder}\n'
            f'Проверьте доступность диска R: и права на запись.\n'
            f'Ошибка: {e}'
        )

    # Подбираем уникальное имя файла
    number = 1
    while True:
        filename = build_filename(date_send, recipient, ext, number if number > 1 else None)
        dest_path = os.path.join(project_folder, filename)
        if not os.path.exists(dest_path):
            break
        number += 1

    shutil.move(temp_path, dest_path)
    return dest_path


def cleanup_temp_file(temp_path):
    """Удаляет временный файл, если он существует."""
    try:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
    except OSError:
        pass
