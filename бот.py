import os
import logging
import requests
from io import BytesIO  # Добавьте этот импорт
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
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

# База данных
user_data_db = {}
location_messages = {}  # Для хранения ID сообщений с картой

# Загрузка переменных окружения
TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

# Координаты места проведения
LOCATION_COORDINATES = (56.50849, 85.02575)  # Широта, долгота

# GitHub репозиторий
GITHUB_REPO_URL = "https://raw.githubusercontent.com/syakimmm/vavilon/main/"

## Фотографии для разделов
PHOTO_ALBUMS = {
    'about': [
        f"{GITHUB_REPO_URL}онас.JPG"
    ],
    'info': [
        f"{GITHUB_REPO_URL}всечтонужно знать о наборах.JPG"
    ]
}

async def download_photo(url: str) -> BytesIO:
    """Загрузка фото из GitHub"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return BytesIO(response.content)
    except Exception as e:
        logger.error(f"Ошибка загрузки фото: {e}")
        raise

async def send_photo_album(update: Update, context: CallbackContext, album_name: str, caption: str):
    """Отправка альбома фотографий"""
    query = update.callback_query
    await query.answer()

    try:
        media_group = []
        for i, url in enumerate(PHOTO_ALBUMS[album_name]):
            photo = await download_photo(url)
            media_group.append(InputMediaPhoto(
                media=photo,
                caption=caption if i == 0 else ""
            ))

        await context.bot.send_media_group(
            chat_id=query.message.chat_id,
            media=media_group
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await query.edit_message_text("⚠️ Не удалось загрузить фотографии")
        return False

async def start(update: Update, context: CallbackContext) -> None:
    """Главное меню"""
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        if user_id in location_messages:
            try:
                await context.bot.delete_message(
                    chat_id=update.callback_query.message.chat_id,
                    message_id=location_messages[user_id]
                )
                del location_messages[user_id]
            except Exception as e:
                logger.error(f"Ошибка удаления карты: {e}")

    keyboard = [
        [InlineKeyboardButton("📝 Записаться", callback_data="signup")],
        [InlineKeyboardButton("ℹ️ О нас", callback_data="about")],
        [InlineKeyboardButton("📌 Информация о наборах", callback_data="info")],
        [InlineKeyboardButton("📍 Адрес", callback_data="location")],
        [InlineKeyboardButton("📞 Контакты", callback_data="contacts")]
    ]

    if update.message:
        await update.message.reply_text(
            "Добро пожаловать! 🩰\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def signup(update: Update, context: CallbackContext) -> int:
    """Начало записи - выбор даты"""
    query = update.callback_query
    await query.answer()

    # Фиксированные даты
    context.user_data['dates'] = [
        "25.08.2025 в 11:00",
        "26.08.2025 в 11:00"
    ]

    keyboard = [
        [InlineKeyboardButton(context.user_data['dates'][0], callback_data="date_0")],
        [InlineKeyboardButton(context.user_data['dates'][1], callback_data="date_1")]
    ]

    await query.edit_message_text(
        "Выберите дату и время:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DATE

async def date_choice(update: Update, context: CallbackContext) -> int:
    """Обработка выбора даты"""
    query = update.callback_query
    await query.answer()

    date_index = int(query.data.split('_')[1])
    context.user_data['date'] = context.user_data['dates'][date_index]

    await query.edit_message_text(
        f"Выбрано: {context.user_data['date']}\n\n"
        "Введите ваш номер телефона для связи:"
    )
    return PHONE

async def phone_input(update: Update, context: CallbackContext) -> int:
    """Ввод телефона"""
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("Введите ваше имя (родителя):")
    return PARENT_NAME

async def parent_name_input(update: Update, context: CallbackContext) -> int:
    """Ввод имени родителя"""
    context.user_data['parent_name'] = update.message.text
    await update.message.reply_text("Введите имя ребенка:")
    return GIRL_NAME

async def girl_name_input(update: Update, context: CallbackContext) -> int:
    """Ввод имени ребенка"""
    context.user_data['girl_name'] = update.message.text
    await update.message.reply_text("Сколько лет ребенку?")
    return AGE

async def age_input(update: Update, context: CallbackContext) -> int:
    """Ввод возраста"""
    context.user_data['age'] = update.message.text
    await update.message.reply_text("Чем раньше занимались? (Опыт занятий):")
    return EXPERIENCE

async def experience_input(update: Update, context: CallbackContext) -> int:
    """Ввод опыта"""
    context.user_data['experience'] = update.message.text
    await update.message.reply_text("Откуда узнали о нас?")
    return SOURCE

async def source_input(update: Update, context: CallbackContext) -> int:
    """Завершение регистрации"""
    context.user_data['source'] = update.message.text
    user_id = update.message.from_user.id

    # Сохраняем данные
    user_data_db[user_id] = context.user_data

    # Уведомление администратору
    admin_message = (
        "✨ Новая запись на пробное занятие!\n\n"
        f"📅 Дата: {context.user_data['date']}\n"
        f"👤 Родитель: {context.user_data['parent_name']}\n"
        f"📞 Телефон: {context.user_data['phone']}\n"
        f"👧 Ребенок: {context.user_data['girl_name']} ({context.user_data['age']} лет)\n"
        f"🎓 Опыт: {context.user_data['experience']}\n"
        f"🔍 Откуда узнали: {context.user_data['source']}\n"
        f"🆔 ID: {user_id}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)

    # Сообщение пользователю с кнопкой отмены
    await update.message.reply_text(
        "✅ Запись оформлена!\n\n"
        f"Мы ждем вас {context.user_data['date']}\n"
        f"По адресу: г. Томск, ул. Иркутский тракт, 86/1\n\n"
        "Если у вас есть вопросы, звоните: +7 (913) 880-84-58 или +7 (983) 236-42-84",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отменить запись", callback_data="cancel")],
            [InlineKeyboardButton("🏠 В меню", callback_data="back")]
        ])
    )
    return ConversationHandler.END

async def cancel_lesson(update: Update, context: CallbackContext) -> None:
    """Отмена записи"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id in user_data_db:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"❌ Запись отменена пользователем {user_id}"
        )
        del user_data_db[user_id]
        await query.edit_message_text("❌ Ваша запись отменена")
    else:
        await query.edit_message_text("У вас нет активных записей")

    await start(update, context)

async def about(update: Update, context: CallbackContext) -> None:
    """Информация о студии с фотоальбомом"""
    about_text = (
        "Мы – Народный ансамбль современного танца «Вавилон»! История нашего коллектива насчитывает 27 лет, а число учениц превышает 200 человек.\n\n"
        "Среди достижений нашего коллектива победы и призерства на крупных чемпионатах России, конкурсах и фестивалях всероссийского и международного уровней. "
        "Все это результат работы команды педагогов-профессионалов своего дела.\n\n"
        "Наши ученицы получают всестороннее развитие в сфере хореографии: в расписании наших воспитанниц хипхоп, классический танец, акробатика, "
        "занятия общей физической подготовки.\n\n"
        "А еще мы большая семья! Наши ученицы постоянно путешествуют по России, выступают на крупных городских событиях, пополняют багаж впечатлений. "
        "Все это они делают вместе с друзьями, которых обрели в коллективе, а педагоги являются верными наставниками не только в мире хореографии, "
        "но и на жизненном пути!\n\n"
        "Больше о нас вы можете узнать в наших социальных сетях!\n"
        "📍VK: https://vk.com/ensemble_vavilon_tomsk\n"
        "📍inst: https://www.instagram.com/vavilon_dance_tomsk?igsh=OTJoNjJmeTF3YjB3&utm_source=qr"
    )

    success = await send_photo_album(
        update, context, 
        album_name='about',
        caption=about_text
    )
    
    if not success:
        await update.message.reply_text(about_text)
    
    if success:
        await show_back_button(update, context)

async def info(update: Update, context: CallbackContext) -> None:
    """Информация о наборах с фотоальбомом"""
    info_text = (
        "❗️Что нужно знать перед наборами?❗️\n\n"
        "1️⃣ В чем прийти на просмотры?\n"
        "Футболка, лосины/шорты (легко тянущиеся), носочки\n\n"
        "2️⃣ Что будет на просмотрах?\n"
        "Просмотры необходимы для того, чтобы педагоги оценили природные данные ребенка и его психологическую готовность к занятиям. "
        "Ребенок вместе с педагогом выполнит ряд элементарных хореографических упражнений, с помощью которых мы увидим природную гибкость ребенка.\n\n"
        "Просмотры проходят БЕЗ РОДИТЕЛЕЙ.\n"
        "(Родитель ожидает в коридоре, затем заходит в зал для общения с руководителем).\n"
        "Нам важно понимать, сможет ли ребенок в дальнейшем находиться на занятиях самостоятельно.\n\n"
        "❗️У детей старше 7 лет приветствуется опыт занятий спортом или хореографией."
    )
    
    success = await send_photo_album(
        update, context, 
        album_name='info',
        caption=info_text
    )
    
    if not success:
        await update.message.reply_text(info_text)

async def location(update: Update, context: CallbackContext) -> None:
    """Адрес студии с картой"""
    query = update.callback_query
    await query.answer()

    message = await context.bot.send_location(
        chat_id=query.message.chat_id,
        latitude=LOCATION_COORDINATES[0],
        longitude=LOCATION_COORDINATES[1]
    )
    location_messages[query.from_user.id] = message.message_id

    await query.edit_message_text(
        "📍 Наш адрес:\nг. Томск, ул. Иркутский тракт, 86/1\nДом культуры «Маяк»",
        reply_markup=back_to_menu_keyboard()
    )

async def contacts(update: Update, context: CallbackContext) -> None:
    """Контакты"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📞 Наши контакты:\n\n"
        "+7 (913) 880-84-58 - Руководитель Плотникова Марина Николаевна\n"
        "+7 (983) 236-42-84 - Юлия",
        reply_markup=back_to_menu_keyboard()
    )

def back_to_menu_keyboard():
    """Клавиатура для возврата в меню"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ В меню", callback_data="back")]
    ])

async def back_to_menu(update: Update, context: CallbackContext) -> None:
    """Возврат в главное меню"""
    await start(update, context)

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # ConversationHandler для записи
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(signup, pattern='^signup$')],
        states={
            DATE: [CallbackQueryHandler(date_choice, pattern='^date_')],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_input)],
            PARENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, parent_name_input)],
            GIRL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, girl_name_input)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_input)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, experience_input)],
            SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, source_input)],
        },
        fallbacks=[
            CallbackQueryHandler(back_to_menu, pattern='^back$')
        ],
    )

    # Регистрация обработчиков
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(about, pattern='^about$'))
    application.add_handler(CallbackQueryHandler(info, pattern='^info$'))
    application.add_handler(CallbackQueryHandler(location, pattern='^location$'))
    application.add_handler(CallbackQueryHandler(contacts, pattern='^contacts$'))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back$'))
    application.add_handler(CallbackQueryHandler(cancel_lesson, pattern='^cancel$'))

    application.run_polling()

if __name__ == '__main__':
    main()