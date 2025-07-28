import os
import logging
import requests
from io import BytesIO
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
    """Загрузка фото из URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return BytesIO(response.content)
    except Exception as e:
        logger.error(f"Ошибка загрузки фото: {e}")
        return None

async def send_photo_album(update: Update, context: CallbackContext, album_name: str, caption: str):
    """Отправка альбома фотографий"""
    try:
        query = update.callback_query
        await query.answer()
        
        media_group = []
        for url in PHOTO_ALBUMS.get(album_name, []):
            photo = await download_photo(url)
            if photo:
                media_group.append(InputMediaPhoto(
                    media=photo,
                    caption=caption if not media_group else ""
                ))
        
        if media_group:
            await context.bot.send_media_group(
                chat_id=query.message.chat_id,
                media=media_group
            )
            return True
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
    
    # Fallback - отправляем только текст если фото не загрузились
    if update.callback_query:
        await update.callback_query.edit_message_text(caption)
    else:
        await update.message.reply_text(caption)
    return False

async def show_back_button(update: Update, context: CallbackContext):
    """Показывает кнопку возврата после альбома"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Выберите действие:",
        reply_markup=back_to_menu_keyboard()
    )

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
        [InlineKeyboardButton("📋 Моя запись", callback_data="my_lesson")],
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

async def my_lesson(update: Update, context: CallbackContext) -> None:
    """Просмотр текущей записи"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_data_db:
        record = user_data_db[user_id]
        keyboard = [
            [InlineKeyboardButton("❌ Отменить запись", callback_data="cancel_my_lesson")],
            [InlineKeyboardButton("◀️ В меню", callback_data="back")]
        ]
        await query.edit_message_text(
            f"📋 Ваша запись:\n\n"
            f"📅 Дата: {record['date']}\n"
            f"👤 Родитель: {record['parent_name']}\n"
            f"📞 Телефон: {record['phone']}\n"
            f"👧 Ребенок: {record['girl_name']} ({record['age']} лет)\n"
            f"🎓 Опыт: {record['experience']}\n"
            f"🔍 Откуда узнали: {record['source']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📝 Записаться", callback_data="signup")],
            [InlineKeyboardButton("◀️ В меню", callback_data="back")]
        ]
        await query.edit_message_text(
            "❌ У вас нет активных записей.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def cancel_my_lesson(update: Update, context: CallbackContext) -> None:
    """Отмена текущей записи"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_data_db:
        # Уведомление администратору
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"❌ Запись отменена пользователем {user_id}\n"
                 f"Дата: {user_data_db[user_id]['date']}\n"
                 f"Родитель: {user_data_db[user_id]['parent_name']}\n"
                 f"Телефон: {user_data_db[user_id]['phone']}"
        )
        
        del user_data_db[user_id]
        await query.edit_message_text(
            "✅ Ваша запись успешно отменена.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Записаться", callback_data="signup")],
                [InlineKeyboardButton("◀️ В меню", callback_data="back")]
            ])
        )
    else:
        await query.edit_message_text(
            "❌ У вас нет активных записей для отмены.",
            reply_markup=back_to_menu_keyboard()
        )

async def signup(update: Update, context: CallbackContext) -> int:
    """Начало записи - выбор даты"""
    query = update.callback_query
    await query.answer()

    # Фиксированные даты
    context.user_data['dates'] = [
        "16.08.2025 с 11:00 до 13:00",
        "23.08.2025 с 11:00 до 13:00",
        "30.08.2025 с 11:00 до 13:00"
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
        "✨ Новая запись!\n\n"
        f"📅 Дата: {context.user_data['date']}\n"
        f"👤 Родитель: {context.user_data['parent_name']}\n"
        f"📞 Телефон: {context.user_data['phone']}\n"
        f"👧 Ребенок: {context.user_data['girl_name']} ({context.user_data['age']} лет)\n"
        f"🎓 Опыт: {context.user_data['experience']}\n"
        f"🔍 Откуда узнали: {context.user_data['source']}\n"
        f"🆔 ID: {user_id}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)

    # Сообщение пользователю без кнопки отмены
    await update.message.reply_text(
        "✅ Запись оформлена!\n\n"
        f"Мы ждем вас {context.user_data['date']}\n"
        f"По адресу: г. Томск, ул. Иркутский тракт, 86/1\n\n"
        "Если у вас есть вопросы, звоните: +7 (913) 880-84-58 - Руководитель Плотникова Марина Николаевна или +7 (983) 236-42-84 - Юлия",
        reply_markup=back_to_menu_keyboard()
    )
    return ConversationHandler.END

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
    
    # Всегда показываем кнопку возврата в меню
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
        "❗️У детей старше 7 лет приветствуется опыт занятий спортом или хореографией.\n\n"
        "Просмотры проходят в порядке живой очереди."
    )
    
    success = await send_photo_album(
        update, context, 
        album_name='info',
        caption=info_text
    )
    
    if not success:
        await update.message.reply_text(info_text)
    
    await show_back_button(update, context)

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
    application.add_handler(CallbackQueryHandler(my_lesson, pattern='^my_lesson$'))
    application.add_handler(CallbackQueryHandler(cancel_my_lesson, pattern='^cancel_my_lesson$'))
    application.add_handler(CallbackQueryHandler(about, pattern='^about$'))
    application.add_handler(CallbackQueryHandler(info, pattern='^info$'))
    application.add_handler(CallbackQueryHandler(location, pattern='^location$'))
    application.add_handler(CallbackQueryHandler(contacts, pattern='^contacts$'))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back$'))

    application.run_polling()

if __name__ == '__main__':
    main()