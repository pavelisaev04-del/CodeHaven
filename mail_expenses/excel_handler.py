import os
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import config


def export_to_excel(records, filter_params=None):
    """
    Экспортирует записи в Excel-файл.
    Возвращает путь к созданному файлу.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Расходы на почту'

    # Стили
    blue_fill = PatternFill(start_color='1D4ED8', end_color='1D4ED8', fill_type='solid')
    light_fill = PatternFill(start_color='EFF6FF', end_color='EFF6FF', fill_type='solid')
    white_font = Font(bold=True, color='FFFFFF', size=10)
    bold_font = Font(bold=True, size=10)
    normal_font = Font(size=10)
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1'),
    )
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)

    now = datetime.now()
    title_text = _build_title(filter_params)

    # Заголовок отчёта (строка 1)
    ws.merge_cells('A1:J1')
    ws['A1'] = title_text
    ws['A1'].font = Font(bold=True, size=14, color='1E3A5F')
    ws['A1'].alignment = center
    ws.row_dimensions[1].height = 30

    # Дата формирования (строка 2)
    ws.merge_cells('A2:J2')
    ws['A2'] = f'Сформировано: {now.strftime("%d.%m.%Y %H:%M")}'
    ws['A2'].font = Font(size=10, color='64748B')
    ws['A2'].alignment = center

    # Пустая строка
    ws.row_dimensions[3].height = 8

    # Заголовки таблицы (строка 4)
    headers = [
        '№', 'Дата отправки', 'РПО письма',
        'Кто отправил', 'Кому отправил',
        'Сумма (руб.)', 'Наименование проекта',
        'Комментарий', 'Дата внесения', 'Файл чека'
    ]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=header)
        cell.font = white_font
        cell.fill = blue_fill
        cell.alignment = center
        cell.border = thin_border

    ws.row_dimensions[4].height = 35

    # Данные (с 5-й строки)
    total_amount = 0.0
    for row_num, record in enumerate(records, 5):
        is_even = (row_num % 2 == 0)
        row_fill = light_fill if is_even else None

        def _cell(col, value, number_format=None, align=None):
            c = ws.cell(row=row_num, column=col, value=value)
            c.font = normal_font
            c.border = thin_border
            c.alignment = align or left
            if row_fill:
                c.fill = row_fill
            if number_format:
                c.number_format = number_format
            return c

        _cell(1, row_num - 4, align=center)
        _cell(2, record.get('date_send', ''), align=center)

        # РПО сохраняем как текст — апостроф заставляет Excel не трогать цифры
        rpo_cell = _cell(3, "'" + str(record.get('rpo', '')), align=center)
        rpo_cell.number_format = '@'

        _cell(4, record.get('sender', '') or '')
        _cell(5, record.get('recipient', '') or '')

        amount = record.get('amount', 0) or 0
        amount_cell = _cell(6, float(amount), number_format='#,##0.00', align=center)
        total_amount += float(amount)

        _cell(7, record.get('project', '') or '')
        _cell(8, record.get('comment', '') or '')
        _cell(9, record.get('created_at', '') or '', align=center)
        _cell(10, record.get('file_path', '') or '')

        ws.row_dimensions[row_num].height = 20

    # Строка итогов
    total_row = len(records) + 5
    ws.merge_cells(f'A{total_row}:E{total_row}')
    total_label = ws.cell(row=total_row, column=1,
                          value=f'ИТОГО записей: {len(records)}')
    total_label.font = bold_font
    total_label.alignment = center
    total_label.fill = PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid')
    total_label.border = thin_border

    total_val = ws.cell(row=total_row, column=6, value=total_amount)
    total_val.font = bold_font
    total_val.number_format = '#,##0.00'
    total_val.alignment = center
    total_val.fill = PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid')
    total_val.border = thin_border

    for col in range(7, 11):
        c = ws.cell(row=total_row, column=col, value='')
        c.border = thin_border
        c.fill = PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid')

    ws.row_dimensions[total_row].height = 25

    # Ширина колонок
    col_widths = [5, 14, 20, 22, 30, 14, 25, 22, 18, 50]
    for col_idx, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Закрепить шапку
    ws.freeze_panes = 'A5'

    # Сохранение файла в папку экспортов
    export_dir = os.path.join(os.path.dirname(config.DATABASE_PATH), 'exports')
    os.makedirs(export_dir, exist_ok=True)
    filename = f'расходы_почта_{now.strftime("%Y%m%d_%H%M%S")}.xlsx'
    export_path = os.path.join(export_dir, filename)
    wb.save(export_path)

    return export_path


def _build_title(filter_params):
    """Формирует заголовок отчёта по параметрам фильтра."""
    base = 'Расходы на почтовые отправления'
    if not filter_params:
        return base

    parts = [base]
    year = filter_params.get('year')
    quarter = filter_params.get('quarter')
    month = filter_params.get('month')
    project = filter_params.get('project')

    if year:
        parts.append(f'за {year} год')
    if quarter:
        parts.append(f'({quarter} квартал)')
    elif month:
        months_ru = [
            '', 'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
            'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'
        ]
        parts.append(f'({months_ru[month]})')
    if project:
        parts.append(f'— проект: {project}')

    return ' '.join(parts)
