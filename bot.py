import os
import asyncio
import logging
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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
DATE, PHONE, PARENT_NAME, GIRL_NAME, AGE, EXPERIENCE, SOURCE = range(7)

# База данных (в продакшене замените на реальную БД)
user_data_db = {}

# Загрузка переменных окружения
TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# ========== ОБРАБОТЧИКИ КОМАНД ==========

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Привет! Я бот для записи на занятия. 🩰\n"
        "Доступные команды:\n"
        "/start - Начать\n"
        "/signup - Записаться\n"
        "/my_lesson - Моя запись\n"
        "/cancel - Отмена\n"
        "/program - Программа\n"
        "/requirements - Что взять\n"
        "/location - Адрес\n"
        "/contacts - Контакты"
    )

async def signup(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("22.05.2025 в 11:00", callback_data="date_2025-05-22_11:00")],
        [InlineKeyboardButton("25.05.2025 в 14:00", callback_data="date_2025-05-25_14:00")],
    ]
    await update.message.reply_text(
        "Выберите дату и время:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DATE

async def date_choice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    date, time = query.data.split('_')[1], query.data.split('_')[2]
    context.user_data['date'] = f"{date} {time}"
    await query.edit_message_text(f"Выбрано: {date} {time}\nВведите телефон:")
    return PHONE

# ========== ЦЕПОЧКА РЕГИСТРАЦИИ ==========

async def phone_input(update: Update, context: CallbackContext) -> int:
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("Имя родителя:")
    return PARENT_NAME

async def parent_name_input(update: Update, context: CallbackContext) -> int:
    context.user_data['parent_name'] = update.message.text
    await update.message.reply_text("Имя ребенка:")
    return GIRL_NAME

async def girl_name_input(update: Update, context: CallbackContext) -> int:
    context.user_data['girl_name'] = update.message.text
    await update.message.reply_text("Возраст ребенка:")
    return AGE

async def age_input(update: Update, context: CallbackContext) -> int:
    context.user_data['age'] = update.message.text
    await update.message.reply_text("Предыдущий опыт:")
    return EXPERIENCE

async def experience_input(update: Update, context: CallbackContext) -> int:
    context.user_data['experience'] = update.message.text
    await update.message.reply_text("Откуда узнали о нас?")
    return SOURCE

async def source_input(update: Update, context: CallbackContext) -> int:
    context.user_data['source'] = update.message.text
    user_id = update.message.from_user.id
    
    # Сохраняем данные
    user_data_db[user_id] = context.user_data
    
    # Уведомление администратору
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"Новая запись:\n{context.user_data}"
    )
    
    await update.message.reply_text(
        "✅ Запись оформлена!\n"
        f"Дата: {context.user_data['date']}\n"
        "Ждем вас!"
    )
    return ConversationHandler.END

# ========== ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ==========

async def my_lesson(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if record := user_data_db.get(user_id):
        await update.message.reply_text(
            f"Ваша запись:\n"
            f"📅 {record['date']}\n"
            f"👧 {record['girl_name']}, {record['age']} лет"
        )
    else:
        await update.message.reply_text("❌ Вы не записаны")

async def cancel_lesson(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in user_data_db:
        del user_data_db[user_id]
        await update.message.reply_text("❌ Запись отменена")
    else:
        await update.message.reply_text("Нет активных записей")

async def cancel_conversation(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Регистрация отменена")
    return ConversationHandler.END

# ========== ИНФОРМАЦИОННЫЕ КОМАНДЫ ==========

async def program(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Программа занятий:\n"
        "1. Разминка\n2. Хореография\n3. Растяжка"
    )

async def requirements(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Возьмите с собой:\n"
        "- Форму для занятий\n"
        "- Воду\n"
        "- Сменную обувь"
    )

async def location(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "📍 Адрес:\n"
        "г. Москва, ул. Танцевальная, 15\n"
        "Студия Vavilon Dance"
    )

async def contacts(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Контакты:\n"
        "Анна: +7 (999) 123-45-67\n"
        "Мария: +7 (999) 765-43-21"
    )

# ========== ЗАПУСК БОТА ==========

def main() -> None:
    # Создаем Application
    application = Application.builder().token(TOKEN).build()

    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('signup', signup)],
        states={
            DATE: [CallbackQueryHandler(date_choice, pattern='^date_')],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_input)],
            PARENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, parent_name_input)],
            GIRL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, girl_name_input)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_input)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, experience_input)],
            SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, source_input)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
    )

    # Регистрация обработчиков
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('my_lesson', my_lesson))
    application.add_handler(CommandHandler('cancel', cancel_lesson))
    application.add_handler(CommandHandler('program', program))
    application.add_handler(CommandHandler('requirements', requirements))
    application.add_handler(CommandHandler('location', location))
    application.add_handler(CommandHandler('contacts', contacts))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()