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
    Возвращает путь к папке «Расходы» внутри папки проекта на сервере.

    Алгоритм:
      1. Ищет подпапку, содержащую слово «расходы» (без учёта регистра и номера),
         например: «10. Расходы», «5. Расходы», «Расходы», «12.Расходы».
      2. Если такая папка найдена — возвращает её путь.
      3. Если не найдена — берёт STORAGE_EXPENSES_SUBFOLDER из config как запасной вариант.

    Пример путей:
        R:\149. БЛИНОВСКАЯ\10. Расходы
        R:\158. ГОНЧАРОВА\5. Расходы
        R:\117. ЛЕОНИДАС\Расходы
    """
    base = getattr(config, 'STORAGE_BASE', None) or getattr(config, 'STORAGE_FOLDER', '.')
    fallback_subfolder = getattr(config, 'STORAGE_EXPENSES_SUBFOLDER', '')

    project_name = project.strip() if project else 'Без_проекта'
    project_path = os.path.join(base, project_name)

    # Ищем подпапку с «расходы» в названии, если папка проекта уже существует
    if os.path.isdir(project_path):
        try:
            for entry in os.scandir(project_path):
                if entry.is_dir() and re.search(r'расход', entry.name, re.IGNORECASE):
                    return entry.path
        except OSError:
            pass

    # Запасной вариант: берём из конфига
    if fallback_subfolder:
        return os.path.join(project_path, fallback_subfolder)
    return project_path


def move_receipt_file(temp_path, date_send, recipient, project):
    """
    Переименовывает и перемещает файл чека в папку проекта на сервере.

    Итоговый путь:
        R:\\[Название проекта]\\10. Расходы\\ГГГГММДД_Отправка почты Получатель.pdf

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
