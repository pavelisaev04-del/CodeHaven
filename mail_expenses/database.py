import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаёт таблицу расходов при первом запуске."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            seq_num     INTEGER,
            date_send   TEXT NOT NULL,
            rpo         TEXT NOT NULL,
            sender      TEXT,
            recipient   TEXT,
            amount      REAL NOT NULL,
            project     TEXT NOT NULL,
            file_path   TEXT,
            created_at  TEXT NOT NULL,
            comment     TEXT
        )
    ''')
    # Уникальный индекс по РПО для проверки дубликатов
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_rpo ON expenses (rpo)
    ''')
    conn.commit()
    conn.close()
    _migrate_add_seq_num()


def _migrate_add_seq_num():
    """
    Добавляет колонку seq_num если её нет (для совместимости с уже созданными БД).
    seq_num — это сквозной порядковый номер строки, как в оригинальной Excel-таблице.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(expenses)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'seq_num' not in columns:
        cursor.execute("ALTER TABLE expenses ADD COLUMN seq_num INTEGER")
        # Назначаем порядковые номера существующим записям по порядку id
        cursor.execute('''
            UPDATE expenses SET seq_num = (
                SELECT COUNT(*) FROM expenses e2 WHERE e2.id <= expenses.id
            )
        ''')
        conn.commit()
    conn.close()


def get_next_seq_num():
    """Возвращает следующий порядковый номер для новой записи."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(seq_num), 0) + 1 FROM expenses")
    num = cursor.fetchone()[0]
    conn.close()
    return num


def check_rpo_duplicate(rpo, exclude_id=None):
    """Возвращает True, если РПО уже есть в базе."""
    conn = get_connection()
    cursor = conn.cursor()
    if exclude_id:
        cursor.execute('SELECT id FROM expenses WHERE rpo = ? AND id != ?', (rpo, exclude_id))
    else:
        cursor.execute('SELECT id FROM expenses WHERE rpo = ?', (rpo,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def add_record(date_send, rpo, sender, recipient, amount, project, file_path, comment=''):
    """Добавляет новую запись. Возвращает ID записи."""
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    # Следующий порядковый номер (продолжение нумерации как в оригинальной таблице)
    cursor.execute("SELECT COALESCE(MAX(seq_num), 0) + 1 FROM expenses")
    seq_num = cursor.fetchone()[0]
    cursor.execute('''
        INSERT INTO expenses (seq_num, date_send, rpo, sender, recipient, amount, project, file_path, created_at, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (seq_num, date_send, str(rpo), sender, recipient, float(amount), project, file_path, created_at, comment))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id


def get_all_records():
    """Возвращает все записи, отсортированные по дате (новые сначала)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM expenses ORDER BY id DESC')
    records = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return records


def get_record_by_id(record_id):
    """Возвращает одну запись по ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM expenses WHERE id = ?', (record_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def _parse_date(date_str):
    """Парсит дату из строки ДД.ММ.ГГГГ."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), '%d.%m.%Y')
    except ValueError:
        return None


def search_records(date_from=None, date_to=None, rpo=None, project=None, sender=None, recipient=None):
    """Поиск записей по фильтрам. Фильтрация по датам выполняется в Python."""
    conn = get_connection()
    cursor = conn.cursor()

    # Текстовые фильтры обрабатываются в SQL
    query = 'SELECT * FROM expenses WHERE 1=1'
    params = []

    if rpo:
        query += ' AND rpo LIKE ?'
        params.append(f'%{rpo}%')
    if project:
        query += ' AND project LIKE ?'
        params.append(f'%{project}%')
    if sender:
        query += ' AND sender LIKE ?'
        params.append(f'%{sender}%')
    if recipient:
        query += ' AND recipient LIKE ?'
        params.append(f'%{recipient}%')

    query += ' ORDER BY id DESC'
    cursor.execute(query, params)
    records = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Фильтрация по датам в Python (формат ДД.ММ.ГГГГ не сортируется как текст)
    if date_from or date_to:
        d_from = _parse_date(date_from)
        d_to = _parse_date(date_to)
        filtered = []
        for r in records:
            d = _parse_date(r['date_send'])
            if d is None:
                continue
            if d_from and d < d_from:
                continue
            if d_to and d > d_to:
                continue
            filtered.append(r)
        return filtered

    return records


def get_report_data(year=None, quarter=None, month=None, project=None):
    """Возвращает записи для отчёта с фильтрацией по периоду и проекту."""
    conn = get_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM expenses WHERE 1=1'
    params = []
    if project:
        query += ' AND project LIKE ?'
        params.append(f'%{project}%')

    cursor.execute(query, params)
    all_records = [dict(r) for r in cursor.fetchall()]
    conn.close()

    filtered = []
    for r in all_records:
        d = _parse_date(r['date_send'])
        if d is None:
            continue
        if year and d.year != year:
            continue
        if month and d.month != month:
            continue
        if quarter:
            record_quarter = (d.month - 1) // 3 + 1
            if record_quarter != quarter:
                continue
        filtered.append(r)

    return filtered


def get_projects_list():
    """Возвращает список уникальных проектов из базы."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT project FROM expenses WHERE project != "" ORDER BY project')
    projects = [row[0] for row in cursor.fetchall()]
    conn.close()
    return projects


def delete_record(record_id):
    """Удаляет запись по ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM expenses WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
