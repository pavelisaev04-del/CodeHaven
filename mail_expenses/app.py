import os
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_file, jsonify
)

import config
import database
import ocr_handler
import file_handler
import excel_handler

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER

# Создаём нужные папки при запуске
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.STORAGE_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)

database.init_db()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), '%d.%m.%Y')
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Главная страница
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    records = database.get_all_records()
    now = datetime.now()

    total_count = len(records)
    total_amount = sum(r.get('amount', 0) or 0 for r in records)

    # Статистика за текущий месяц
    month_records = [
        r for r in records
        if _parse_date(r.get('date_send'))
        and _parse_date(r['date_send']).month == now.month
        and _parse_date(r['date_send']).year == now.year
    ]
    month_amount = sum(r.get('amount', 0) or 0 for r in month_records)

    # Последние 5 записей для виджета на главной
    latest = records[:5]

    ocr_status = ocr_handler.get_ocr_status()

    return render_template(
        'index.html',
        total_count=total_count,
        total_amount=total_amount,
        month_count=len(month_records),
        month_amount=month_amount,
        latest=latest,
        ocr_status=ocr_status,
        current_year=now.year,
        current_month=now.month,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Загрузка чека
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')

    # Проверка: файл выбран?
    if 'file' not in request.files or request.files['file'].filename == '':
        flash('Выберите файл для загрузки.', 'error')
        return redirect(request.url)

    uploaded_file = request.files['file']

    if not allowed_file(uploaded_file.filename):
        allowed = ', '.join(sorted(config.ALLOWED_EXTENSIONS))
        flash(f'Неподдерживаемый формат. Разрешены: {allowed}', 'error')
        return redirect(request.url)

    # Сохраняем во временную папку с уникальным именем
    ext = uploaded_file.filename.rsplit('.', 1)[1].lower()
    temp_name = f'{uuid.uuid4().hex}.{ext}'
    temp_path = os.path.join(config.UPLOAD_FOLDER, temp_name)
    uploaded_file.save(temp_path)

    # Пробуем распознать текст
    ocr_text = ''
    ocr_error = ''
    try:
        ocr_text = ocr_handler.extract_text(temp_path) or ''
    except RuntimeError as e:
        # OCR не установлен — предупреждаем, но продолжаем (ввод вручную)
        ocr_error = str(e)
        flash(f'OCR недоступен: {ocr_error}. Заполните поля вручную.', 'warning')
    except Exception as e:
        ocr_error = str(e)
        flash(f'Ошибка при распознавании: {ocr_error}. Заполните поля вручную.', 'warning')

    # Разбираем текст на поля
    parsed = ocr_handler.parse_receipt(ocr_text)

    if ocr_text and not any(parsed.values()):
        flash('Текст распознан, но данные не найдены. Заполните поля вручную.', 'warning')

    # Сохраняем в сессию
    session['receipt'] = {
        'temp_file': temp_name,
        'original_filename': uploaded_file.filename,
        'date_send': parsed.get('date_send', ''),
        'rpo': parsed.get('rpo', ''),
        'sender': parsed.get('sender', ''),
        'recipient': parsed.get('recipient', ''),
        'amount': parsed.get('amount', ''),
        'project': parsed.get('project', ''),
        'comment': '',
    }

    return redirect(url_for('review'))


# ─────────────────────────────────────────────────────────────────────────────
# Форма проверки распознанных данных
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/review', methods=['GET'])
def review():
    data = session.get('receipt')
    if not data:
        flash('Нет данных для проверки. Загрузите файл.', 'error')
        return redirect(url_for('upload'))

    projects = database.get_projects_list()
    return render_template('review.html', data=data, projects=projects)


# ─────────────────────────────────────────────────────────────────────────────
# Сохранение записи
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/save', methods=['POST'])
def save():
    receipt = session.get('receipt')
    if not receipt:
        flash('Сессия истекла. Загрузите файл заново.', 'error')
        return redirect(url_for('upload'))

    # Читаем форму
    date_send = request.form.get('date_send', '').strip()
    rpo = request.form.get('rpo', '').strip()
    sender = request.form.get('sender', '').strip()
    recipient = request.form.get('recipient', '').strip()
    amount_raw = request.form.get('amount', '').strip().replace(',', '.')
    project = request.form.get('project', '').strip()
    comment = request.form.get('comment', '').strip()

    errors = []

    # ── Валидация ──
    if not date_send:
        errors.append('Укажите дату отправки.')
    elif _parse_date(date_send) is None:
        errors.append('Дата должна быть в формате ДД.ММ.ГГГГ (например: 22.01.2026).')

    if not rpo:
        errors.append('Укажите РПО письма.')

    if not amount_raw:
        errors.append('Укажите сумму.')
    else:
        try:
            amount = float(amount_raw)
            if amount <= 0:
                errors.append('Сумма должна быть больше нуля.')
        except ValueError:
            errors.append('Сумма должна быть числом (например: 245.50).')
            amount = 0.0

    if not project:
        errors.append('Укажите наименование проекта.')

    # Проверка дубликата РПО
    if rpo and database.check_rpo_duplicate(rpo):
        errors.append(
            f'РПО «{rpo}» уже есть в базе данных. '
            'Если это другое письмо, проверьте номер.'
        )

    if errors:
        # Обновляем данные сессии введёнными значениями
        session['receipt'] = {
            **receipt,
            'date_send': date_send,
            'rpo': rpo,
            'sender': sender,
            'recipient': recipient,
            'amount': amount_raw,
            'project': project,
            'comment': comment,
        }
        session.modified = True
        projects = database.get_projects_list()
        for msg in errors:
            flash(msg, 'error')
        return render_template('review.html', data=session['receipt'], projects=projects)

    # ── Перемещение файла ──
    temp_path = os.path.join(config.UPLOAD_FOLDER, receipt['temp_file'])
    try:
        new_path = file_handler.move_receipt_file(
            temp_path=temp_path,
            date_send=date_send,
            recipient=recipient,
            project=project,
        )
    except FileNotFoundError:
        flash('Временный файл не найден. Загрузите чек заново.', 'error')
        session.pop('receipt', None)
        return redirect(url_for('upload'))
    except Exception as e:
        flash(f'Ошибка при перемещении файла: {e}', 'error')
        projects = database.get_projects_list()
        return render_template('review.html', data=session['receipt'], projects=projects)

    # ── Сохранение в БД ──
    try:
        record_id = database.add_record(
            date_send=date_send,
            rpo=rpo,
            sender=sender,
            recipient=recipient,
            amount=float(amount_raw),
            project=project,
            file_path=new_path,
            comment=comment,
        )
    except Exception as e:
        flash(
            f'Файл перемещён, но запись не сохранена в БД: {e}. '
            f'Файл находится по пути: {new_path}',
            'error'
        )
        session.pop('receipt', None)
        return redirect(url_for('expenses'))

    # ── Запись в основной Excel-файл на сервере ──
    record_for_excel = {
        'seq_num': database.get_next_seq_num() - 1,  # уже добавлен в БД
        'date_send': date_send,
        'rpo': rpo,
        'sender': sender,
        'recipient': recipient,
        'amount': float(amount_raw),
        'project': project,
    }
    try:
        excel_handler.append_to_master_excel(record_for_excel)
    except RuntimeError as e:
        # Excel недоступен — запись в БД уже сохранена, просто предупреждаем
        flash(f'Запись сохранена в базу данных, но в Excel не добавлена: {e}', 'warning')
    except Exception as e:
        flash(f'Запись сохранена в базу данных, но в Excel не добавлена: {e}', 'warning')

    session.pop('receipt', None)
    flash(f'Запись #{record_id} успешно сохранена!', 'success')
    return redirect(url_for('expenses'))


@app.route('/cancel-upload', methods=['POST'])
def cancel_upload():
    """Отменяет загрузку и удаляет временный файл."""
    receipt = session.get('receipt')
    if receipt and receipt.get('temp_file'):
        file_handler.cleanup_temp_file(
            os.path.join(config.UPLOAD_FOLDER, receipt['temp_file'])
        )
    session.pop('receipt', None)
    flash('Загрузка отменена.', 'info')
    return redirect(url_for('index'))


# ─────────────────────────────────────────────────────────────────────────────
# Таблица расходов
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/expenses')
def expenses():
    records = database.get_all_records()
    total_amount = sum(r.get('amount', 0) or 0 for r in records)
    return render_template('expenses.html', records=records, total_amount=total_amount)


@app.route('/delete/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    database.delete_record(record_id)
    flash(f'Запись #{record_id} удалена.', 'info')
    return redirect(url_for('expenses'))


# ─────────────────────────────────────────────────────────────────────────────
# Поиск и фильтрация
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/search')
def search():
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    rpo = request.args.get('rpo', '').strip()
    project = request.args.get('project', '').strip()
    sender = request.args.get('sender', '').strip()
    recipient = request.args.get('recipient', '').strip()

    has_filters = any([date_from, date_to, rpo, project, sender, recipient])
    records = []

    if has_filters:
        records = database.search_records(
            date_from=date_from or None,
            date_to=date_to or None,
            rpo=rpo or None,
            project=project or None,
            sender=sender or None,
            recipient=recipient or None,
        )

    projects = database.get_projects_list()
    total_amount = sum(r.get('amount', 0) or 0 for r in records)

    return render_template(
        'search.html',
        records=records,
        projects=projects,
        has_filters=has_filters,
        total_amount=total_amount,
        filters={
            'date_from': date_from,
            'date_to': date_to,
            'rpo': rpo,
            'project': project,
            'sender': sender,
            'recipient': recipient,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Отчёты
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/reports')
def reports():
    now = datetime.now()
    year = request.args.get('year', str(now.year))
    quarter = request.args.get('quarter', '')
    month = request.args.get('month', '')
    project_filter = request.args.get('project', '')

    try:
        year_int = int(year) if year else None
    except ValueError:
        year_int = now.year

    filter_params = {
        'year': year_int,
        'quarter': int(quarter) if quarter else None,
        'month': int(month) if month else None,
        'project': project_filter or None,
    }

    records = database.get_report_data(**filter_params)
    total_amount = sum(r.get('amount', 0) or 0 for r in records)
    total_count = len(records)

    # Группировка по проектам
    by_project = {}
    for r in records:
        p = r.get('project') or 'Без проекта'
        if p not in by_project:
            by_project[p] = {'count': 0, 'amount': 0.0}
        by_project[p]['count'] += 1
        by_project[p]['amount'] += r.get('amount', 0) or 0

    # Группировка по месяцам
    months_ru = [
        '', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    by_month = {}
    for r in records:
        d = _parse_date(r.get('date_send'))
        if d:
            key = f'{months_ru[d.month]} {d.year}'
            sort_key = f'{d.year}{d.month:02d}'
            if key not in by_month:
                by_month[key] = {'count': 0, 'amount': 0.0, 'sort': sort_key}
            by_month[key]['count'] += 1
            by_month[key]['amount'] += r.get('amount', 0) or 0

    # Сортируем месяцы по хронологии
    by_month = dict(sorted(by_month.items(), key=lambda x: x[1]['sort']))

    projects = database.get_projects_list()
    years = list(range(2020, now.year + 2))

    return render_template(
        'reports.html',
        total_amount=total_amount,
        total_count=total_count,
        by_project=by_project,
        by_month=by_month,
        projects=projects,
        years=years,
        months_ru=months_ru,
        current_filters={
            'year': year,
            'quarter': quarter,
            'month': month,
            'project': project_filter,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Экспорт в Excel
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/export')
def export():
    now = datetime.now()
    year = request.args.get('year', '')
    quarter = request.args.get('quarter', '')
    month = request.args.get('month', '')
    project = request.args.get('project', '')

    filter_params = {
        'year': int(year) if year else None,
        'quarter': int(quarter) if quarter else None,
        'month': int(month) if month else None,
        'project': project or None,
    }

    records = database.get_report_data(**filter_params)

    if not records:
        # Если фильтров нет — экспортируем всё
        records = database.get_all_records()

    if not records:
        flash('Нет данных для экспорта.', 'warning')
        return redirect(url_for('reports'))

    try:
        export_path = excel_handler.export_to_excel(records, filter_params)
        return send_file(
            export_path,
            as_attachment=True,
            download_name=os.path.basename(export_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except Exception as e:
        flash(f'Ошибка при экспорте в Excel: {e}', 'error')
        return redirect(url_for('reports'))


# ─────────────────────────────────────────────────────────────────────────────
# API: список проектов (для автодополнения)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/projects')
def api_projects():
    return jsonify(database.get_projects_list())


# ─────────────────────────────────────────────────────────────────────────────
# Обработчик больших файлов
# ─────────────────────────────────────────────────────────────────────────────

@app.errorhandler(413)
def file_too_large(e):
    flash(f'Файл слишком большой. Максимальный размер: {config.MAX_CONTENT_LENGTH // 1024 // 1024} МБ.', 'error')
    return redirect(url_for('upload'))


if __name__ == '__main__':
    print(f'Сервер запущен: http://localhost:{config.PORT}')
    print(f'Для доступа из сети: http://<IP-адрес-сервера>:{config.PORT}')
    print('Нажмите Ctrl+C для остановки.')
    app.run(host=config.HOST, port=config.PORT, debug=False)
