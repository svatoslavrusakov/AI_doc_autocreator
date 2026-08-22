import os
import sys
import uuid
from typing import Sequence
from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
import requests

# Импортируем наши изолированные модули
from models import Customer, Job
from pdf_generator import render_act_pdf

@tool
def update_act_pdf(customer: Customer, jobs: list[Job]) -> str:
    """
    Создает или ОБНОВЛЯЕТ файл акта с актуальными данными заказчика и списком работ.
    Имя файла формируется автоматически как output/act_НазваниеКомпании.pdf
    Вызывай эту функцию каждый раз, когда пользователь просит создать акт, добавить работу, изменить сумму или реквизиты.
    """
    try:
        # Передаем только customer и jobs, чтобы сработала динамическая генерация имени
        filepath, total_sum = render_act_pdf(customer, jobs)
        print(f"\n🔄 [SYSTEM TOOL] Файл {filepath} обновлен! Итоговая сумма: {total_sum} руб.")
        
        # Берем только базовое имя файла для красивого ответа пользователю
        filename = os.path.basename(filepath)
        return f"Акт перегенерирован и сохранен как {filename}. В нем {len(jobs)} позиций на общую сумму {total_sum} руб."
    except Exception as e:
        return f"Ошибка при обновлении PDF: {e}"



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
Каждый раз при слове "Сделай", "Создание", "Добавление", "изменение" или "удаление" ты должен запустить инструмент update_act_pdf.

Вот реквизиты Заказчика из файла:
{req_text}

Правила работы:
Каждый раз когда тебя вызывают при создании, добавлении, изменении или удалении, ты должен запустить инструмент update_act_pdf.
Каждый раз когда тебя вызывают при создании, добавлении, изменении или удалении, ты должен запустить формирование нового акта.
1. Твоя единственная цель — поддерживать акт в актуальном состоянии.
2. Спроси у пользователя, какие работы внести в акт и их стоимость.
3. Каждые изменения (добавление работы, изменение цены, редактирование данных) должны ВСЕГДА приводить к вызову инструмента `update_act_pdf`.
4. Имя и отчество подписанта сокращай до инициалов (например, Иванов А.Е.).
5. Название компании оборачивай в кавычки-ёлочки «название».
"""

    print("🚀 AI-Агент управления Актом запущен!")
    print("💡 Совет: открывайте файл output/act.pdf в браузере (Chrome/Firefox) для просмотра изменений на лету.")
    print("----------------------------------------------------------------------------------------------------")

    agent_response = agent.invoke(system_prompt)

    while True:
        print(f"\n🤖 Агент: {agent_response}")
        user_input = input("\n👤 Ты: ")

        if user_input.lower() in ["выход", "exit", "quit"]:
            print("Запрос на полную очистку контекста в KoboldCPP...")
            #Запрос на удаление контекста.
            try:
                # Отправляем пустой промпт с требованием полностью очистить кэш (trim: 0)
                # Это принудительно сбросит внутреннюю память KoboldCPP для вашей сессии
                url = "http://localhost:5001/api/v1/generate" # или http://127.0.0
                payload = {
                    "prompt": "",
                    "trim": 0,
                    "max_context_length": 1,
                    "max_length": 1
                }
                requests.post(url, json=payload, timeout=5)
                print("✅ Команда сброса успешно отправлена.")
            except Exception as e:
                print(f"❌ Не удалось отправить команду очистки: {e}")
                
            print("Сессия завершена.")
            break

        agent_response = agent.invoke(user_input)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nЗавершение работы.")
