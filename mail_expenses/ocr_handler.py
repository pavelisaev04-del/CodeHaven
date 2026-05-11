import re
import os
from datetime import datetime

# Попытка импортировать pytesseract — если не установлен, OCR недоступен
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Попытка импортировать PyMuPDF — для работы с PDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

import config

# Прописываем путь к Tesseract, только если библиотека доступна
if TESSERACT_AVAILABLE:
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH


def extract_text(file_path):
    """
    Извлекает текст из файла (PDF или изображение).
    Возвращает строку с распознанным текстом.
    """
    ext = file_path.rsplit('.', 1)[-1].lower()

    if ext == 'pdf':
        return _extract_from_pdf(file_path)
    elif ext in ('png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif'):
        return _extract_from_image(file_path)
    else:
        raise ValueError(f'Неподдерживаемый формат файла: {ext}')


def _extract_from_pdf(file_path):
    """Извлекает текст из PDF. Сначала пробует встроенный текст, потом OCR."""
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError(
            'Библиотека PyMuPDF не установлена. '
            'Выполните: pip install pymupdf'
        )

    doc = fitz.open(file_path)
    text = ''
    for page in doc:
        text += page.get_text()
    doc.close()

    # Если встроенного текста нет — пробуем OCR через изображение страниц
    if len(text.strip()) < 30:
        text = _ocr_pdf_pages(file_path)

    return text


def _ocr_pdf_pages(file_path):
    """Рендерит страницы PDF в изображения и запускает OCR."""
    if not TESSERACT_AVAILABLE:
        return ''

    doc = fitz.open(file_path)
    full_text = ''

    for page in doc:
        # 300 DPI даёт хорошее качество для OCR
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_path = file_path + f'_ocr_page{page.number}.png'
        pix.save(img_path)
        try:
            img = Image.open(img_path)
            page_text = pytesseract.image_to_string(img, lang='rus+eng', config='--psm 6')
            full_text += page_text + '\n'
        except Exception:
            pass
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    doc.close()
    return full_text


def _extract_from_image(file_path):
    """Извлекает текст из изображения через OCR."""
    if not TESSERACT_AVAILABLE:
        raise RuntimeError(
            'Tesseract OCR не установлен или pytesseract недоступен. '
            'Установите Tesseract и выполните: pip install pytesseract pillow'
        )
    img = Image.open(file_path)
    text = pytesseract.image_to_string(img, lang='rus+eng', config='--psm 6')
    return text


def parse_receipt(text):
    """
    Разбирает текст чека и ищет нужные поля.
    Возвращает словарь с найденными данными.
    """
    result = {
        'date_send': '',
        'rpo': '',
        'sender': '',
        'recipient': '',
        'amount': '',
        'project': '',
    }

    if not text:
        return result

    # Нормализуем текст: убираем лишние пробелы
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    result['date_send'] = _find_date(text) or ''
    result['rpo'] = _find_rpo(text) or ''
    result['sender'] = _find_sender(text) or ''
    result['recipient'] = _find_recipient(text) or ''
    result['amount'] = _find_amount(text) or ''

    return result


def _find_date(text):
    """Ищет дату в формате ДД.ММ.ГГГГ."""
    # Сначала ищем рядом с характерными словами
    keyword_pattern = (
        r'(?:дат[аы]|принято|отправлено|дата\s+приёма|дата\s+приема)'
        r'[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})'
    )
    match = re.search(keyword_pattern, text, re.IGNORECASE)
    if match:
        return _normalize_date(match.group(1))

    # Ищем любую дату в тексте
    all_dates = re.findall(r'\b(\d{2}[.\-/]\d{2}[.\-/]\d{4})\b', text)
    for date_str in all_dates:
        normalized = _normalize_date(date_str)
        if normalized:
            return normalized

    return None


def _normalize_date(date_str):
    """Приводит дату к формату ДД.ММ.ГГГГ, проверяет корректность."""
    date_str = date_str.replace('-', '.').replace('/', '.')
    try:
        d = datetime.strptime(date_str, '%d.%m.%Y')
        # Отклоняем даты ранее 2000 года и позже текущего + 1 год
        if d.year < 2000 or d.year > datetime.now().year + 1:
            return None
        return d.strftime('%d.%m.%Y')
    except ValueError:
        return None


def _find_rpo(text):
    """Ищет трек-номер РПО."""
    # Почта России: 14 цифр
    # Международный формат: XX999999999XX (2 буквы + 9 цифр + 2 буквы)
    patterns = [
        # С ключевым словом
        r'(?:рпо|идентификатор|шпи|штрих[\s\-]?код|трек)[:\s#№]+(\d{14})',
        r'(?:рпо|идентификатор|шпи)[:\s#№]+([A-Za-z]{2}\d{9}[A-Za-z]{2})',
        # Без ключевого слова — ищем 14 цифр подряд
        r'\b(\d{14})\b',
        # Международный формат без ключевого слова
        r'\b([A-Z]{2}\d{9}[A-Z]{2})\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()

    return None


def _find_sender(text):
    """Ищет отправителя."""
    patterns = [
        r'(?:отправитель|от\s+кого|кто\s+отправил)[:\s]+([^\n]{3,80})',
        r'(?:sender)[:\s]+([^\n]{3,80})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip().rstrip(',.;')
            if len(name) >= 3:
                return name
    return None


def _find_recipient(text):
    """Ищет получателя."""
    patterns = [
        r'(?:получатель|кому|адресат|recipient)[:\s]+([^\n]{3,100})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip().rstrip(',.;')
            if len(name) >= 3:
                return name
    return None


def _find_amount(text):
    """Ищет сумму оплаты."""
    patterns = [
        # С ключевым словом и суммой X,XX или X.XX
        r'(?:итого|к\s+оплате|оплачено|сумма|стоимость)[:\s]+(\d{1,6}[.,]\d{2})',
        # Число с рублями рядом
        r'(\d{1,6}[.,]\d{2})\s*(?:руб|₽)',
        # Число с ключевым словом (без копеек)
        r'(?:итого|к\s+оплате)[:\s]+(\d{1,6})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '.')
            try:
                val = float(amount_str)
                # Отклоняем слишком маленькие и слишком большие суммы
                if 0 < val < 1_000_000:
                    return f'{val:.2f}'
            except ValueError:
                pass
    return None


def get_ocr_status():
    """Возвращает информацию о доступности OCR-компонентов."""
    status = {
        'pytesseract': TESSERACT_AVAILABLE,
        'pymupdf': PYMUPDF_AVAILABLE,
        'tesseract_path': config.TESSERACT_PATH,
    }
    if TESSERACT_AVAILABLE:
        try:
            version = pytesseract.get_tesseract_version()
            status['tesseract_version'] = str(version)
        except Exception as e:
            status['tesseract_error'] = str(e)
    return status
