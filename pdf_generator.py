import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from config import FONT_REGULAR, FONT_BOLD, DEFAULT_PDF_PATH, OUTPUT_DIR
from models import Customer, Job

def render_act_pdf(customer: Customer, jobs: list[Job], filepath: str = DEFAULT_PDF_PATH):
    """Создает или обновляет файл Акт выполненных работ в формате PDF"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Эта штука отвечает за формирование имени файла
    # Если путь не передан, формируем его динамически на основе компании
    if filepath is None:
        # Очищаем название компании от кавычек («», "", ''), двоеточий и прочих запрещенных символов
        clean_company_name = re.sub(r'[\\/*?:"<>|«»\'\s]+', '_', customer.name)
        # Убираем лишние подчеркивания по краям
        clean_company_name = clean_company_name.strip('_')
        
        filename = f"act_{clean_company_name}.pdf"
        filepath = os.path.join(OUTPUT_DIR, filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    # Заголовок
    c.setFont(FONT_BOLD, 14)
    c.drawCentredString(width / 2, height - 50, "АКТ № 1 приёмки-сдачи оказанных услуг")
    
    # Дата проведения
    c.setFont(FONT_REGULAR, 9)
    c.drawString(50, height - 70, "г. Москва")
    c.drawRightString(width - 50, height - 70, "«17» августа 2026 г.")

    # Данные Заказчика
    c.setFont(FONT_BOLD, 10)
    c.drawString(50, height - 95, "Заказчик:")
    c.setFont(FONT_REGULAR, 9)
    c.drawString(110, height - 95, f"{customer.name}, ИНН: {customer.INN}, ОГРН: {customer.OGRN}")
    c.drawString(50, height - 110, f"Адрес: {customer.address}")
    c.drawString(50, height - 125, f"Банк: {customer.bank.name}, БИК: {customer.bank.BIC}, Р/с: {customer.bank.current_account}")

    # Линия
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.gray)
    c.line(50, height - 140, width - 50, height - 140)

    # Table Header
    c.setFont(FONT_BOLD, 10)
    c.drawString(50, height - 160, "№")
    c.drawString(80, height - 160, "Наименование оказанных услуг / выполненных работ")
    c.drawRightString(width - 50, height - 160, "Сумма (руб.)")

    c.line(50, height - 168, width - 50, height - 168)

    y = height - 185
    total_sum = 0
    c.setFont(FONT_REGULAR, 9)

    for idx, job in enumerate(jobs, 1):
        c.drawString(50, y, str(idx))
        c.drawString(80, y, str(job.task)[:65])
        c.drawRightString(width - 50, y, f"{job.price:,}".replace(",", " "))
        total_sum += job.price
        y -= 18

    c.line(50, y + 5, width - 50, y + 5)
    y -= 15

    # Итого
    c.setFont(FONT_BOLD, 10)
    total_str = f"ИТОГО: {total_sum:,} руб.".replace(",", " ")
    c.drawRightString(width - 50, y, total_str)

    y -= 30
    c.setFont(FONT_REGULAR, 8)
    c.drawString(50, y, "Вышеперечисленные услуги выполнены полностью и в срок. Заказчик претензий по качеству не имеет.")

    # Блок подписей
    y -= 45
    c.setFont(FONT_BOLD, 9)
    c.drawString(50, y, "Заказчик:")
    c.drawString(width - 200, y, "Исполнитель:")
    
    y -= 20
    c.setFont(FONT_REGULAR, 9)
    c.drawString(50, y, f"________________ / {customer.signatory} /")
    c.drawString(width - 200, y, "________________ / Русаков /")

    c.save()
    return filepath, total_sum
