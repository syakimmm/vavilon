!pip install python-telegram-bot

import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
)
import logging
import nest_asyncio

# Разрешаем вложенные event loops для Colab
nest_asyncio.apply()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
DATE, PHONE, PARENT_NAME, GIRL_NAME, AGE, EXPERIENCE, SOURCE = range(7)

# "База данных" (временное хранилище)
user_data_db = {}

# Ваши данные
TOKEN = "7634997769:AAHenc7fdR-7Cec6vW1To04L2a82LBIS3lc"  # Токен бота
ADMIN_CHAT_ID = "ВАШ_CHAT_ID"  # Замените на ваш ID в Telegram

# [Все асинхронные функции остаются такими же, как в предыдущем коде]
# ...

async def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # Обработчик диалога записи
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("signup", signup)],
        states={
            DATE: [CallbackQueryHandler(date_choice, pattern="^date_.*$")],  # Добавлен pattern
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_input)],
            PARENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, parent_name_input)],
            GIRL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, girl_name_input)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_input)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, experience_input)],
            SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, source_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_message=False  # Явно указываем для избежания предупреждения
    )

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("my_lesson", my_lesson))
    application.add_handler(CommandHandler("cancel", cancel_lesson))
    application.add_handler(CommandHandler("program", program))
    application.add_handler(CommandHandler("requirements", requirements))
    application.add_handler(CommandHandler("location", location))
    application.add_handler(CommandHandler("contacts", contacts))

    # Запуск бота
    await application.run_polling()

if __name__ == '__main__':
    # Запускаем асинхронный main
    asyncio.run(main())