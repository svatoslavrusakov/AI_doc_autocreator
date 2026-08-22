from dataclasses import asdict, dataclass
import json
import os
import sys
from typing import Sequence
import uuid

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
# Импорты для генерации PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Подключаем системные шрифты Windows с поддержкой кириллицы
try:
    pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
    pdfmetrics.registerFont(
        TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf")
    )
    FONT_REGULAR = "Arial"
    FONT_BOLD = "Arial-Bold"
except Exception:
    FONT_REGULAR = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"


# --- 1. СТРУКТУРЫ ДАННЫХ ---


@dataclass
class Bank:
    name: str  # наименование банка
    BIC: str  # БИК
    current_account: str  # расчётный счёт
    corporate_account: str  # корреспондентский счёт


@dataclass
class Customer:
    name: str  # полное название юр. лица
    INN: str  # ИНН
    OGRN: str  # ОГРН или ОГРНИП
    address: str  # юридический адрес
    signatory: str  # подписант (например, Иванов А.Е.)
    bank: Bank  # банковские реквизиты


@dataclass
class Job:
    task: str  # выполненная задача
    price: int  # цена за задачу


# --- 2. ГЕНЕРАТОР PDF-АКТА ---


def render_act_pdf(customer: Customer, jobs: list[Job], filepath: str = "output/act.pdf"):
    """Создает или обновляет файл Акт выполненных работ в формате PDF"""
    os.makedirs("output", exist_ok=True)

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

    # Таблица выполненных работ
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
        c.drawString(80, y, str(job.task)[:65])  # Ограничиваем длину строки
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


# --- 3. ИНСТРУМЕНТ АГЕНТА (Tool) ---

@tool
def update_act_pdf(customer: Customer, jobs: list[Job]) -> str:
    """
    Создает или ОБНОВЛЯЕТ файл 'output/act.pdf' с актуальными данными заказчика и списком работ.
    Вызывай эту функцию каждый раз, когда пользователь просит создать акт, добавить работу, изменить сумму или реквизиты.
    """
    try:
        filepath, total_sum = render_act_pdf(customer, jobs)
        print(f"\n🔄 [SYSTEM TOOL] Файл {filepath} обновлен! Итоговая сумма: {total_sum} руб.")
        return f"Акт перегенерирован и сохранен в {filepath}. В нем {len(jobs)} позиций на общую сумму {total_sum} руб."
    except Exception as e:
        return f"Ошибка при обновлении PDF: {e}"


# --- 4. ОБЕРТКА АГЕНТА ---

class LLMAgent:
    def __init__(self, model: LanguageModelLike, tools: Sequence[BaseTool]):
        self._model = model
        self._agent = create_react_agent(model, tools=tools, checkpointer=InMemorySaver())
        self._config = {"configurable": {"thread_id": uuid.uuid4().hex}}

    def invoke(self, content: str) -> str:
        response = self._agent.invoke(
            {"messages": [{"role": "user", "content": content}]},
            config=self._config
        )
        return response["messages"][-1].content


# --- 5. ГЛАВНЫЙ ЦИКЛ ---

def main():
    try:
        requisites_file = sys.argv[1]
    except IndexError:
        requisites_file = "req.txt"

    if os.path.exists(requisites_file):
        with open(requisites_file, "r", encoding="utf-8") as f:
            req_text = f.read()
    else:
        req_text = "ООО 'Вектор', ИНН 7701123456, ОГРН 1027700012345, г. Москва, ул. Ленина 1. Подписант: Петров И.С., Банк: ПАО Сбербанк, БИК: 044525225, Р/с: 40702810938000012345"

    llm = ChatOpenAI(
        base_url="http://localhost:5001/v1",
        api_key="not-needed",
        model="qwen2.5-1.5b",
        temperature=0.1
    )

    agent = LLMAgent(llm, tools=[update_act_pdf])

    system_prompt = f"""
Ты специализированный AI-агент для управления «Актом выполненных работ».
Твоя задача — формировать и в режиме реального времени обновлять PDF-акт (файл output/act.pdf).

Вот реквизиты Заказчика из файла:
{req_text}

Правила работы:
Каждый раз когда тебя вызывают при добавлении, изменении изменение цены или изменении данных, ты должен запустить формирование нового акта.
1. Твоя единственная цель — поддерживать акт в актуальном состоянии.
2. Спроси у пользователя, какие работы внести в акт и их стоимость.
3. Каждые изменения (добавление работы, изменение цены, редактирование данных) должны ВСЕГДА приводить к вызову инструмента `update_act_pdf`.
4. Имя и отчество подписанта сокращай до инициалов (например, Иванов А.Е.).
5. Название компании оборачивай в кавычки-ёлочки «название».
6. Если пользователь называет курс — используй формулировку "Обучение одного сотрудника на курсе «Хардкорная веб-разработка»", стоимость 170000 руб.
"""

    print("🚀 AI-Агент управления Актом запущен!")
    print("💡 Совет: открывайте файл output/act.pdf в браузере (Chrome/Firefox) для просмотра изменений на лету.")
    print("----------------------------------------------------------------------------------------------------")

    agent_response = agent.invoke(system_prompt)

    while True:
        print(f"\n🤖 Агент: {agent_response}")
        user_input = input("\n👤 Ты: ")

        if user_input.lower() in ["выход", "exit", "quit"]:
            print("Сессия завершена.")
            break

        agent_response = agent.invoke(user_input)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nЗавершение работы.")