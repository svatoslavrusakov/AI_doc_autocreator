import re
from datetime import date
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from config import FONT_REGULAR, FONT_BOLD, OUTPUT_DIR
from models import Customer, Job


def render_act_pdf(customer: Customer, jobs: list[Job], filepath=None, *, city: str = "", act_date: str | None = None):
    """Создать акт с переносами текста и страниц. Явный filepath обновляет файл."""
    if not city.strip():
        raise ValueError("Укажите город составления акта")
    day = date.fromisoformat(act_date) if act_date else date.today()
    if any(type(job.price) is not int or job.price < 0 for job in jobs):
        raise ValueError("Стоимость должна быть целым неотрицательным числом рублей")
    if filepath is None:
        company = re.sub(r'[^\w-]+', '_', customer.name).strip('_')[:60] or 'customer'
        filepath = Path(OUTPUT_DIR) / f"act_{company}_{uuid4().hex}.pdf"
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    style = ParagraphStyle('body', fontName=FONT_REGULAR, fontSize=10, leading=15, splitLongWords=True)
    heading = ParagraphStyle('heading', parent=style, fontName=FONT_BOLD, fontSize=13, leading=18)
    story = []
    def add(text, bold=False):
        story.append(Paragraph(escape(str(text)).replace('\n', '<br/>'), heading if bold else style))
        story.append(Spacer(1, 10))
    add('АКТ № 1 приёмки-сдачи оказанных услуг', True)
    add(f'Город: {city}, дата: {day:%d.%m.%Y}')
    add(f'Заказчик: {customer.name}, ИНН: {customer.INN}, ОГРН: {customer.OGRN}')
    add(f'Адрес: {customer.address}')
    add(f'Банк: {customer.bank.name}, БИК: {customer.bank.BIC}, р/с: {customer.bank.current_account}, к/с: {customer.bank.corporate_account}')
    rows = [[Paragraph(text, style) for text in ('№', 'Наименование оказанных услуг / выполненных работ', 'Сумма (руб.)')]]
    for i, job in enumerate(jobs, 1):
        rows.append([str(i), Paragraph(escape(job.task).replace('\n', '<br/>'), style), f'{job.price:,}'.replace(',', ' ')])
    table = Table(rows, colWidths=[30, A4[0] - 230, 100], repeatRows=1, splitInRow=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_REGULAR),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.gray),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.gray),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.extend([table, Spacer(1, 15)])
    total = sum(job.price for job in jobs)
    add(f'ИТОГО: {total:,} руб.'.replace(',', ' '), True)
    add('Услуги выполнены полностью и в срок. Заказчик претензий по качеству не имеет.')
    story.append(KeepTogether([Paragraph(escape(f'Заказчик: ______________ / {customer.signatory} /'), style), Spacer(1, 20), Paragraph('Исполнитель: ______________ / ______________ /', style)]))
    SimpleDocTemplate(str(path), pagesize=A4, rightMargin=50, leftMargin=50).build(story)
    return str(path), total
