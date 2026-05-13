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
    """
    Ищет дату в тексте чека Почты России.
    Поддерживает форматы: ДД.ММ.ГГГГ и ДД.ММ.ГГ (внизу кассового чека).
    """
    # Формат ДД.ММ.ГГ ЧЧ:ММ — дата внизу кассового чека Почты России
    # Например: 01.04.26 18:57
    short_year = re.search(r'\b(\d{2}\.\d{2}\.\d{2})\s+\d{2}:\d{2}', text)
    if short_year:
        normalized = _normalize_date_short(short_year.group(1))
        if normalized:
            return normalized

    # Дата рядом с ключевыми словами, полный год
    keyword_pattern = (
        r'(?:дат[аы]|принято|отправлено|дата\s+приёма|дата\s+приема)'
        r'[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})'
    )
    match = re.search(keyword_pattern, text, re.IGNORECASE)
    if match:
        return _normalize_date(match.group(1))

    # Любая дата с полным годом
    all_dates = re.findall(r'\b(\d{2}[.\-/]\d{2}[.\-/]\d{4})\b', text)
    for date_str in all_dates:
        normalized = _normalize_date(date_str)
        if normalized:
            return normalized

    return None


def _normalize_date(date_str):
    """Приводит дату ДД.ММ.ГГГГ к стандартному формату, проверяет корректность."""
    date_str = date_str.replace('-', '.').replace('/', '.')
    try:
        d = datetime.strptime(date_str, '%d.%m.%Y')
        if d.year < 2000 or d.year > datetime.now().year + 1:
            return None
        return d.strftime('%d.%m.%Y')
    except ValueError:
        return None


def _normalize_date_short(date_str):
    """
    Приводит дату ДД.ММ.ГГ к формату ДД.ММ.ГГГГ.
    Например: 01.04.26 → 01.04.2026
    """
    date_str = date_str.replace('-', '.').replace('/', '.')
    try:
        d = datetime.strptime(date_str, '%d.%m.%y')
        if d.year < 2000 or d.year > datetime.now().year + 1:
            return None
        return d.strftime('%d.%m.%Y')
    except ValueError:
        return None


def _find_rpo(text):
    """
    Ищет трек-номер РПО в чеке Почты России.
    Форматы:
      - '1 РПО № 80110619875732' (кассовый чек)
      - 'РПО: 80110619875732'
      - просто 14 цифр подряд
      - международный: RX123456789RU
    """
    patterns = [
        # Кассовый чек Почты России: "1 РПО № XXXXXXXXXXXXXX"
        r'\d+\s+рпо\s*[№#]?\s*(\d{14})',
        # Стандартные метки
        r'(?:рпо|идентификатор|шпи|штрих[\s\-]?код|трек)[:\s#№]+(\d{14})',
        r'(?:рпо|идентификатор|шпи)[:\s#№]+([A-Za-z]{2}\d{9}[A-Za-z]{2})',
        # 14 цифр без ключевого слова
        r'\b(\d{14})\b',
        # Международный формат
        r'\b([A-Za-z]{2}\d{9}[A-Za-z]{2})\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()
    return None


def _find_sender(text):
    """
    Ищет отправителя.
    В кассовом чеке Почты России: 'Отправитель: Фамилия Имя Отчество'
    """
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
    """
    Ищет получателя.
    В кассовом чеке Почты России поле называется 'Адресат:'.
    Берём только ФИО/название, не адрес доставки.
    """
    patterns = [
        # Кассовый чек Почты России: "Адресат: Фамилия И.О."
        r'адресат[:\s]+([^\n]{3,100})',
        # Стандартные варианты
        r'(?:получатель|кому|recipient)[:\s]+([^\n]{3,100})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip().rstrip(',.;')
            # Отбрасываем строки, похожие на адрес (содержат цифры и слова "г.", "ул." и т.д.)
            if len(name) >= 2 and not re.search(r'\d{6}', name):
                return name
    return None


def _find_amount(text):
    """
    Ищет итоговую сумму оплаты.
    В кассовом чеке Почты России приоритет:
      1. ИТОГ =133.60  (строка с жирным ИТОГ)
      2. БЕЗНАЛИЧНЫМИ =133.60
      3. К ОПЛАТЕ ...
      4. Любое число с рублями
    Избегаем 'Тариф за пересылку' — это не итоговая сумма.
    """
    # Формат кассового чека: "ИТОГ =133.60" или "ИТОГ =133,60"
    itog = re.search(r'итог[оа]?\s*=\s*(\d{1,6}[.,]\d{2})', text, re.IGNORECASE)
    if itog:
        return _parse_amount(itog.group(1))

    # БЕЗНАЛИЧНЫМИ =133.60
    beznal = re.search(r'безналичными\s*=?\s*(\d{1,6}[.,]\d{2})', text, re.IGNORECASE)
    if beznal:
        return _parse_amount(beznal.group(1))

    # К оплате / Оплачено
    oplata = re.search(
        r'(?:к\s+оплате|оплачено|итого)[:\s=]+(\d{1,6}[.,]\d{2})',
        text, re.IGNORECASE
    )
    if oplata:
        return _parse_amount(oplata.group(1))

    # Число с рублями — последнее найденное (обычно итог внизу чека)
    all_amounts = re.findall(r'(\d{1,6}[.,]\d{2})\s*(?:руб|₽)', text, re.IGNORECASE)
    if all_amounts:
        return _parse_amount(all_amounts[-1])

    return None


def _parse_amount(amount_str):
    """Преобразует строку суммы в число с двумя знаками."""
    try:
        val = float(amount_str.replace(',', '.'))
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
