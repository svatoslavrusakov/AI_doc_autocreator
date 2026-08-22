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

# --- 1. СТРУКТУРЫ ДАННЫХ (Pydantic / Dataclasses) ---


@dataclass
class Bank:
    """Банковские реквизиты заказчика"""

    name: str  # наименование банка
    BIC: str  # БИК
    current_account: str  # расчётный счёт
    corporate_account: str  # корреспондентский счёт


@dataclass
class Customer:
    """Заказчик"""

    name: str  # полное название юр. лица (например, ООО «Рога и копыта»)
    INN: str  # ИНН
    OGRN: str  # ОГРН или ОГРНИП
    address: str  # юридический адрес
    signatory: str  # подписант (например, Иванов А.Е.)
    bank: Bank  # банковские реквизиты


@dataclass
class Job:
    task: str  # выполненная задача
    price: int  # цена за задачу


# --- 2. ИНСТРУМЕНТЫ АГЕНТА (Tools) ---


@tool
def generate_pdf_act(customer: Customer, jobs: list[Job]) -> str:
    """
    Генерирует Акт выполненных работ в формате JSON/PDF.
    Принимает данные клиента и список выполненных работ.
    """
    act_data = {
        "document_type": "Акт выполненных работ",
        "customer": asdict(customer),
        "jobs": [asdict(j) for j in jobs],
        "total_sum": sum(j.price for j in jobs),
    }

    os.makedirs("output", exist_ok=True)
    file_path = os.path.join("output", "act.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(act_data, f, ensure_ascii=False, indent=2)

    print(
        f"\n✅ [TOOL] Акт успешно сформирован и сохранен в файл: {file_path}"
    )
    return f"Акт успешно сгенерирован и сохранен в {file_path}. Итоговая сумма: {act_data['total_sum']} руб."


@tool
def generate_pdf_invoice(customer: Customer, jobs: list[Job]) -> str:
    """
    Генерирует Счёт на оплату в формате JSON/PDF.
    Принимает данные клиента и список выполненных работ.
    """
    invoice_data = {
        "document_type": "Счёт на оплату",
        "customer": asdict(customer),
        "jobs": [asdict(j) for j in jobs],
        "total_sum": sum(j.price for j in jobs),
    }

    os.makedirs("output", exist_ok=True)
    file_path = os.path.join("output", "invoice.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(invoice_data, f, ensure_ascii=False, indent=2)

    print(
        f"\n✅ [TOOL] Счёт успешно сформирован и сохранен в файл: {file_path}"
    )
    return f"Счёт успешно сгенерирован и сохранен в {file_path}. Итоговая сумма: {invoice_data['total_sum']} руб."


# --- 3. ОБЕРТКА ДЛЯ LANGGRAPH АГЕНТА ---


class LLMAgent:

    def __init__(self, model: LanguageModelLike, tools: Sequence[BaseTool]):
        self._model = model
        self._agent = create_react_agent(
            model, tools=tools, checkpointer=InMemorySaver()
        )
        self._config = {"configurable": {"thread_id": uuid.uuid4().hex}}

    def invoke(self, content: str) -> str:
        """Отправляет сообщение в диалог агента"""
        response = self._agent.invoke(
            {"messages": [{"role": "user", "content": content}]},
            config=self._config,
        )
        return response["messages"][-1].content


# --- 4. ОСНОВНОЙ ЦИКЛ ПРОГРАММЫ ---


def main():
    # Проверяем аргументы командной строки
    try:
        requisites_file = sys.argv[1]
    except IndexError:
        requisites_file = "req.txt"  # Значение по умолчанию, если не передали аргумент

    # Читаем файл с реквизитами
    if os.path.exists(requisites_file):
        with open(requisites_file, "r", encoding="utf-8") as f:
            req_text = f.read()
    else:
        req_text = "ООО 'Вектор', ИНН 7701123456, ОГРН 1027700012345, г. Москва, ул. Ленина 1. Подписант: Петров И.С."

    # Инициализируем модель через локальный KoboldCPP (OpenAI API формат)
    llm = ChatOpenAI(
        base_url="http://localhost:5001/v1",
        api_key="not-needed",
        model="qwen2.5-1.5b",
        temperature=0.1,
    )

    # Создаем агента с нашими инструментами
    agent = LLMAgent(llm, tools=[generate_pdf_act, generate_pdf_invoice])

    system_prompt = f"""
Ты профессиональный бухгалтерский AI-агент.
Твоя задача — узнать у пользователя, какой документ он хочет сгенерировать (акт, счёт или оба).

Вот реквизиты контрагента из файла:
{req_text}

Правила работы:
1. Запроси у пользователя список выполненных работ и их стоимость.
2. Если пользователь указывает курс, то используй формулировку: "Обучение одного сотрудника на курсе «Хардкорная веб-разработка»", стоимость 170000 руб.
3. Имя и отчество подписанта сокращай до инициалов (например, Иванов А.Е.).
4. Название компании оборачивай в кавычки-ёлочки «название».
5. Как только получишь все данные — вызови нужный инструмент (generate_pdf_act или generate_pdf_invoice).
"""

    print("🤖 AI-Агент инициализирован и готов к работе!")
    print("--------------------------------------------------")

    # Первичное обращение агента к пользователю
    agent_response = agent.invoke(system_prompt)

    while True:
        print(f"\n🤖 Агент: {agent_response}")
        user_input = input("\n👤 Ты: ")

        if user_input.lower() in ["выход", "exit", "quit"]:
            print("До свидания!")
            break

        agent_response = agent.invoke(user_input)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nРабота завершена.")