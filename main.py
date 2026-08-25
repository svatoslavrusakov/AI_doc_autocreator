import os
import sys
from typing import Sequence
import uuid

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
import requests

# Импортируем твои модули
from models import Customer, Job
from pdf_generator import render_act_pdf

# --- 1. ТУЛ ДЛЯ АГЕНТА ---


@tool
def update_act_pdf(customer: Customer, jobs: list[Job]) -> str:
    """Создает или ОБНОВЛЯЕТ файл акта с актуальными данными заказчика и списком работ.

    Имя файла формируется автоматически как output/act_НазваниеКомпании.pdf
    Вызывай эту функцию каждый раз, когда пользователь просит создать акт,
    добавить работу, изменить сумму или реквизиты.
    """
    try:
        filepath, total_sum = render_act_pdf(customer, jobs)
        print(
            f"\n🔄 [SYSTEM TOOL] Файл {filepath} обновлен! Итоговая сумма: {total_sum} руб."
        )

        filename = os.path.basename(filepath)
        return f"Акт перегенерирован и сохранен как {filename}. В нем {len(jobs)} позиций на общую сумму {total_sum} руб."
    except Exception as e:
        return f"Ошибка при обновлении PDF: {e}"


# --- 2. КЛАСС АГЕНТА ---


class LLMAgent:

    def __init__(
        self,
        model: LanguageModelLike,
        tools: Sequence[BaseTool],
        system_prompt: str = "",
    ):
        self._model = model
        self._agent = create_react_agent(
            model,
            tools=tools,
            prompt=system_prompt,  # Передаем системный промпт прямо в агента
            checkpointer=InMemorySaver(),
        )
        self._config = {"configurable": {"thread_id": uuid.uuid4().hex}}

    def invoke(self, content: str) -> str:
        response = self._agent.invoke(
            {"messages": [{"role": "user", "content": content}]},
            config=self._config,
        )
        return response["messages"][-1].content


# --- 3. ЧТЕНИЕ РЕКВИЗИТОВ И ФОРМИРОВАНИЕ ПРОМПТА ---

requisites_file = sys.argv[1] if len(sys.argv) > 1 else "req.txt"

if os.path.exists(requisites_file):
    with open(requisites_file, "r", encoding="utf-8") as f:
        req_text = f.read()
else:
    req_text = "ООО 'Вектор', ИНН 7701123456, ОГРН 1027700012345, г. Москва, ул. Ленина 1. Подписант: Петров И.С., Банк: ПАО Сбербанк, БИК: 044525225, Р/с: 40702810938000012345"

SYSTEM_PROMPT = f"""
Ты специализированный AI-агент для управления «Актом выполненных работ».
Твоя задача — формировать и в режиме реального времени обновлять PDF-акт (файлы в папке output/).

Вот реквизиты Заказчика из файла:
{req_text}

Правила работы:
Каждый раз при слове "Сделай", "Создание", "Добавление", "изменение" или "удаление" ты должен запустить инструмент update_act_pdf.
1. Твоя единственная цель — поддерживать акт в актуальном состоянии.
2. Спроси у пользователя, какие работы внести в акт и их стоимость.
3. Каждые изменения (добавление работы, изменение цены, редактирование данных) должны ВСЕГДА приводить к вызову инструмента `update_act_pdf`.
4. Имя и отчество подписанта сокращай до инициалов (например, Иванов А.Е.).
5. Название компании оборачивай в кавычки-ёлочки «название».
"""

# --- 4. ИНИЦИАЛИЗАЦИЯ МОДЕЛИ И ЭКСПОРТИРУЕМОГО ОБЪЕКТА AGENT ---

llm = ChatOpenAI(
    base_url="http://localhost:5001/v1",
    api_key="not-needed",
    model="qwen2.5-1.5b",
    temperature=0.1,
)

# Этот объект импортируется в app.py (from main import agent)
agent = LLMAgent(llm, tools=[update_act_pdf], system_prompt=SYSTEM_PROMPT)


# --- 5. КОНСОЛЬНЫЙ РЕЖИМ (ЕСЛИ ЗАПУСКАТЬ НАПРЯМУЮ: python main.py) ---


def main():
    print("🚀 AI-Агент управления Актом запущен в консольном режиме!")
    print(
        "------------------------------------------------------------------------------------"
    )

    while True:
        user_input = input("\n👤 Ты: ")

        if user_input.lower() in ["выход", "exit", "quit"]:
            print("Запрос на полную очистку контекста в KoboldCPP...")
            try:
                url = "http://localhost:5001/api/v1/generate"
                payload = {
                    "prompt": "",
                    "trim": 0,
                    "max_context_length": 1,
                    "max_length": 1,
                }
                requests.post(url, json=payload, timeout=5)
                print("✅ Команда сброса успешно отправлена.")
            except Exception as e:
                print(f"❌ Не удалось отправить команду очистки: {e}")

            print("Сессия завершена.")
            break

        response = agent.invoke(user_input)
        print(f"\n🤖 Агент: {response}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nЗавершение работы.")
