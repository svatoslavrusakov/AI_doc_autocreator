import logging
import glob
import os
import streamlit as st

# Локальная конфигурация и фабрика агентов
from config import OUTPUT_DIR
from main import create_agent

if "agent" not in st.session_state:
    st.session_state.agent = create_agent()

# Настройка страницы
st.set_page_config(
    page_title="AI Agent - Генератор Актов", page_icon="📄", layout="wide"
)
st.title("🤖 AI-Агент управления Актом")

# код отключения анимаий
# 2. ПРЯМО СЮДА ВСТАВЛЯЕТСЯ ЭТОТ CSS-КОД:
st.markdown(
    """
    <style>
        /* Отключаем все анимации */
        *, *::before, *::after {
            animation: none !important;
            transition: none !important;
        }

        /* Убираем бегающего человечка в правом верхнем углу */
        [data-testid="stStatusWidget"] {
            display: none !important;
            visibility: hidden !important;
        }

        /* Убираем серую верхнюю полосу Streamlit */
        header[data-testid="stHeader"] {
            display: none !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)
# Коне кода для отключения анимий

# Хранение истории чата в сессии браузера
if "messages" not in st.session_state:
    st.session_state.messages = []

# Разметка страницы: Чат (слева) и Файлы (справа)
col_chat, col_files = st.columns([2, 1])


# --- ПРАВАЯ КОЛОНКА: СКАЧИВАНИЕ PDF-ФАЙЛОВ ---
with col_files:
    st.subheader("📁 Сформированные PDF")

    if os.path.exists(OUTPUT_DIR):
        pdf_files = glob.glob(os.path.join(OUTPUT_DIR, "*.pdf"))
        # Сортировка: самые свежие файлы вверху
        pdf_files.sort(key=os.path.getmtime, reverse=True)

        if pdf_files:
            for path in pdf_files:
                filename = os.path.basename(path)
                with open(path, "rb") as f:
                    st.download_button(
                        label=f"📥 Скачать {filename}",
                        data=f,
                        file_name=filename,
                        mime="application/pdf",
                        key=path,
                        use_container_width=True,
                    )
        else:
            st.info("Папка output пуста")
    else:
        st.info("Папка output не найдена")


# --- ЛЕВАЯ КОЛОНКА: ИНТЕРФЕЙС ЧАТА ---
with col_chat:
    # Отрисовка истории сообщений
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Поле ввода команды
    if user_input := st.chat_input("Введите команду..."):
        # Сообщение пользователя
        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user"):
            st.write(user_input)

        # Вызов твоего агента из main.py
        with st.chat_message("assistant"):
            with st.spinner("Агент выполняет запрос..."):
                try:
                    reply = st.session_state.agent.invoke(user_input)
                except Exception as exc:
                    logging.getLogger(__name__).error("Agent request failed: %s", type(exc).__name__)
                    reply = "Ошибка запроса: проверьте KoboldCpp и поддержку вызова инструментов."
                st.write(reply)

        # Ответ агента
        st.session_state.messages.append(
            {"role": "assistant", "content": reply}
        )
        st.rerun()