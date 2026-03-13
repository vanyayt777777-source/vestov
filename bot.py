import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
from datetime import datetime
import sqlite3
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 512361845

if not TOKEN:
    raise ValueError("Не найден токен бота! Установите переменную окружения BOT_TOKEN")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния
class MailingStates(StatesGroup):
    waiting_for_message = State()

class CustomEmojiStates(StatesGroup):
    waiting_for_emoji = State()

# База данных
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  joined_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups
                 (chat_id INTEGER PRIMARY KEY,
                  chat_title TEXT,
                  chat_type TEXT,
                  added_date TEXT)''')
    conn.commit()
    conn.close()

# Добавление пользователя в БД
def add_user(user_id, username, first_name, last_name):
    try:
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, joined_date) VALUES (?, ?, ?, ?, ?)",
                  (user_id, username, first_name, last_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error adding user: {e}")

# Добавление группы в БД
def add_group(chat_id, chat_title, chat_type):
    try:
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO groups (chat_id, chat_title, chat_type, added_date) VALUES (?, ?, ?, ?)",
                  (chat_id, chat_title, chat_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error adding group: {e}")

# Получение статистики
def get_stats():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM groups")
    groups_count = c.fetchone()[0]
    conn.close()
    return users_count, groups_count

# Получение всех пользователей для рассылки
def get_all_users():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

# Клавиатура главного меню
def main_keyboard():
    keyboard = [
        [types.KeyboardButton(text="👤 Узнать свой ID")],
        [types.KeyboardButton(text="👥 Узнать ID группы"), types.KeyboardButton(text="📢 Узнать ID канала")],
        [types.KeyboardButton(text="🤖 Узнать ID бота"), types.KeyboardButton(text="⭐ ID премиум смайлика")],
        [types.KeyboardButton(text="ℹ️ Информация")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Клавиатура админ-панели
def admin_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📨 Сделать рассылку", callback_data="admin_mailing")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    return keyboard

# Проверка на админа
def is_admin(user_id):
    return user_id == ADMIN_ID

# Команда старт
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"🤖 Я бот для получения ID различных сущностей Telegram:\n"
        f"• 👤 ID пользователей\n"
        f"• 👥 ID групп\n"
        f"• 📢 ID каналов\n"
        f"• 🤖 ID ботов\n"
        f"• ⭐ ID премиум смайликов\n\n"
        f"Выберите нужную опцию в меню ниже:"
    )
    
    await message.answer(welcome_text, reply_markup=main_keyboard())

# Обработка кнопки "Узнать свой ID"
@dp.message(F.text == "👤 Узнать свой ID")
async def get_my_id(message: Message):
    user = message.from_user
    text = (
        f"🆔 <b>Твой ID:</b> <code>{user.id}</code>\n\n"
        f"👤 Имя: {user.first_name}\n"
        f"📝 Фамилия: {user.last_name if user.last_name else 'не указана'}\n"
        f"🔗 Username: @{user.username if user.username else 'отсутствует'}\n"
        f"🤖 Бот: {'Да' if user.is_bot else 'Нет'}"
    )
    await message.answer(text, parse_mode="HTML")

# Обработка кнопки "Узнать ID группы"
@dp.message(F.text == "👥 Узнать ID группы")
async def get_group_id_info(message: Message):
    text = (
        "👥 <b>Как узнать ID группы:</b>\n\n"
        "1️⃣ Добавьте бота в группу\n"
        "2️⃣ Сделайте бота администратором (для получения полной информации)\n"
        "3️⃣ Отправьте в группу любое сообщение\n"
        "4️⃣ Перешлите это сообщение сюда\n\n"
        "📎 <b>Или просто:</b>\n"
        "• Перешлите любое сообщение из группы сюда\n"
        "• Бот автоматически определит ID группы\n\n"
        "📌 <i>ID группы будет показан в формате: -100xxxxxxxxxx</i>"
    )
    await message.answer(text, parse_mode="HTML")

# Обработка кнопки "Узнать ID канала"
@dp.message(F.text == "📢 Узнать ID канала")
async def get_channel_id_info(message: Message):
    text = (
        "📢 <b>Как узнать ID канала:</b>\n\n"
        "1️⃣ Добавьте бота в канал\n"
        "2️⃣ Сделайте бота администратором\n"
        "3️⃣ Опубликуйте пост в канале\n"
        "4️⃣ Перешлите этот пост сюда\n\n"
        "📎 <b>Альтернативный способ:</b>\n"
        "• Если у канала есть username, можно использовать:\n"
        "  <code>@username канала</code>\n\n"
        "📌 <i>ID канала обычно начинается с -100</i>"
    )
    await message.answer(text, parse_mode="HTML")

# Обработка кнопки "Узнать ID бота"
@dp.message(F.text == "🤖 Узнать ID бота")
async def get_bot_id_info(message: Message):
    text = (
        "🤖 <b>Как узнать ID бота:</b>\n\n"
        "1️⃣ <b>ID этого бота:</b> <code>" + str((await bot.get_me()).id) + "</code>\n\n"
        "2️⃣ <b>Чтобы узнать ID другого бота:</b>\n"
        "• Перешлите сообщение от того бота сюда\n"
        "• Или ответьте на сообщение того бота командой /id\n"
        "• Упомяните бота в сообщении (@username бота)\n\n"
        "📎 <b>Пример:</b>\n"
        "Отправьте: @BotFather\n"
        "Бот покажет ID этого бота"
    )
    await message.answer(text, parse_mode="HTML")

# Обработка кнопки "ID премиум смайлика"
@dp.message(F.text == "⭐ ID премиум смайлика")
async def get_custom_emoji_info(message: Message, state: FSMContext):
    text = (
        "⭐ <b>Узнать ID премиум смайлика</b>\n\n"
        "Отправьте мне премиум смайлик (кастомный эмодзи),\n"
        "и я покажу его уникальный ID.\n\n"
        "📌 <i>Премиум смайлики выглядят как обычные эмодзи,\n"
        "но имеют уникальный идентификатор в Telegram</i>\n\n"
        "🔍 <b>Как отправить:</b>\n"
        "• Просто вставьте смайлик в сообщение\n"
        "• Или используйте смайлик из списка Premium стикеров"
    )
    
    # Создаем клавиатуру для отмены
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_emoji")]
    ])
    
    await message.answer(text, parse_mode="HTML", reply_markup=cancel_keyboard)
    await state.set_state(CustomEmojiStates.waiting_for_emoji)

# Обработка отмены для премиум смайликов
@dp.callback_query(F.data == "cancel_emoji")
async def cancel_emoji(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Поиск ID смайлика отменен.\n"
        "Вы можете вернуться в главное меню.",
        reply_markup=None
    )
    await callback.answer()

# Обработка получения премиум смайлика
@dp.message(CustomEmojiStates.waiting_for_emoji)
async def process_custom_emoji(message: Message, state: FSMContext):
    if not message.entities:
        await message.answer(
            "❌ Это не смайлик или сообщение не содержит форматирования.\n"
            "Пожалуйста, отправьте именно премиум смайлик.\n\n"
            "Попробуйте еще раз или нажмите /cancel"
        )
        return
    
    emoji_id = None
    emoji_char = None
    
    # Ищем кастомный эмодзи в entities
    for entity in message.entities:
        if entity.type == "custom_emoji":
            emoji_id = entity.custom_emoji_id
            # Получаем сам символ эмодзи
            if entity.offset < len(message.text):
                emoji_char = message.text[entity.offset:entity.offset + entity.length]
            break
    
    if emoji_id:
        text = (
            f"⭐ <b>Информация о премиум смайлике</b>\n\n"
            f"🔢 <b>ID смайлика:</b>\n<code>{emoji_id}</code>\n\n"
            f"😊 <b>Символ:</b> {emoji_char if emoji_char else 'Не определен'}\n\n"
            f"📌 <b>Как использовать:</b>\n"
            f"• Для отправки смайлика используйте:\n"
            f"<code>&lt;emoji id={emoji_id}&gt;</code>\n\n"
            f"• В ботах можно использовать этот ID\n"
            f"для создания кнопок с кастомными эмодзи"
        )
        await message.answer(text, parse_mode="HTML")
    else:
        await message.answer(
            "❌ Это не премиум смайлик.\n"
            "Пожалуйста, отправьте именно кастомный эмодзи Telegram Premium.\n\n"
            "Попробуйте еще раз или используйте кнопку '🔙 Отмена'"
        )
        return
    
    await state.clear()

# Обработка кнопки "Информация"
@dp.message(F.text == "ℹ️ Информация")
async def get_info(message: Message):
    bot_info = await bot.get_me()
    users_count, groups_count = get_stats()
    
    text = (
        "ℹ️ <b>О боте</b>\n\n"
        f"🤖 <b>Информация:</b>\n"
        f"• Имя: {bot_info.first_name}\n"
        f"• Username: @{bot_info.username}\n"
        f"• ID: <code>{bot_info.id}</code>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• 👤 Пользователей: {users_count}\n"
        f"• 👥 Групп/каналов: {groups_count}\n\n"
        f"⚙️ <b>Функции:</b>\n"
        f"• Определение ID пользователей\n"
        f"• Определение ID групп и каналов\n"
        f"• Определение ID ботов\n"
        f"• Определение ID премиум смайликов\n"
        f"• Админ-панель с рассылкой\n\n"
        f"👑 <b>Админ:</b> <code>{ADMIN_ID}</code>\n\n"
        f"📌 <b>Команды:</b>\n"
        f"/start - Запустить бота\n"
        f"/admin - Админ-панель\n"
        f"/id - Узнать ID (для ответа на сообщение)"
    )
    await message.answer(text, parse_mode="HTML")

# Команда для быстрого получения ID
@dp.message(Command("id"))
async def cmd_id(message: Message):
    if message.reply_to_message:
        # Если это ответ на сообщение
        if message.reply_to_message.from_user:
            user = message.reply_to_message.from_user
            text = (
                f"🆔 <b>ID пользователя:</b> <code>{user.id}</code>\n"
                f"👤 Имя: {user.first_name}\n"
                f"🔗 Username: @{user.username if user.username else 'отсутствует'}"
            )
        elif message.reply_to_message.forward_from_chat:
            chat = message.reply_to_message.forward_from_chat
            text = (
                f"📢 <b>ID чата/канала:</b> <code>{chat.id}</code>\n"
                f"📌 Название: {chat.title}\n"
                f"🔤 Тип: {chat.type}"
            )
        else:
            text = "❌ Не удалось определить ID"
    else:
        text = (
            "❌ Используйте команду /id в ответ на сообщение,\n"
            "чтобы узнать ID пользователя или чата."
        )
    
    await message.answer(text, parse_mode="HTML")

# Команда админ-панели
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await message.answer(
        "🔐 Админ-панель\nВыберите действие:",
        reply_markup=admin_keyboard()
    )

# Обработка callback от админ-панели
@dp.callback_query(F.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    action = callback.data.replace("admin_", "")
    
    if action == "stats":
        users_count, groups_count = get_stats()
        text = (
            f"📊 <b>Статистика бота</b>\n\n"
            f"👤 Пользователей: {users_count}\n"
            f"👥 Групп/каналов: {groups_count}\n"
            f"📅 Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_keyboard())
        await callback.answer()
    
    elif action == "mailing":
        await callback.message.edit_text(
            "📨 Отправьте сообщение для рассылки всем пользователям:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]
            ])
        )
        await state.set_state(MailingStates.waiting_for_message)
        await callback.answer()
    
    elif action == "back":
        await callback.message.edit_text(
            "🔐 Админ-панель\nВыберите действие:",
            reply_markup=admin_keyboard()
        )
        await callback.answer()
        await state.clear()

# Обработка сообщений для рассылки
@dp.message(MailingStates.waiting_for_message)
async def process_mailing(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа.")
        await state.clear()
        return
    
    users = get_all_users()
    success = 0
    failed = 0
    
    status_msg = await message.answer("📤 Начинаю рассылку...")
    
    for user_id in users:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success += 1
        except Exception as e:
            failed += 1
            logging.error(f"Failed to send to {user_id}: {e}")
        
        await asyncio.sleep(0.05)
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n"
        f"📨 Отправлено: {success}\n"
        f"❌ Ошибок: {failed}"
    )
    
    await state.clear()

# Обработка всех сообщений (для автоматического определения ID)
@dp.message()
async def handle_message(message: Message):
    # Добавляем пользователя в БД
    user = message.from_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    
    # Проверяем на наличие упоминаний ботов
    if message.entities:
        for entity in message.entities:
            # Если есть упоминание пользователя
            if entity.type == "mention":
                username = message.text[entity.offset:entity.offset + entity.length].replace('@', '')
                text = f"🔍 Упоминание пользователя @{username}\nПопробуйте переслать его сообщение для получения ID"
                await message.answer(text)
    
    # Если это пересланное сообщение от пользователя
    if message.forward_from:
        user = message.forward_from
        text = (
            f"🔄 <b>Информация о пересланном сообщении</b>\n\n"
            f"👤 Отправитель: {user.first_name}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📝 Username: @{user.username if user.username else 'отсутствует'}\n"
            f"🤖 Бот: {'Да' if user.is_bot else 'Нет'}"
        )
        await message.answer(text, parse_mode="HTML")
    
    # Если это пересланное сообщение из группы/канала
    elif message.forward_from_chat:
        chat = message.forward_from_chat
        add_group(chat.id, chat.title, chat.type)
        
        chat_type_emoji = "👥" if chat.type == "group" or chat.type == "supergroup" else "📢"
        
        text = (
            f"{chat_type_emoji} <b>Информация о чате/канале</b>\n\n"
            f"📌 Название: {chat.title}\n"
            f"🆔 ID: <code>{chat.id}</code>\n"
            f"🔤 Тип: {chat.type}\n"
            f"🔗 Username: @{chat.username if chat.username else 'отсутствует'}\n"
            f"👥 Участников: {'неизвестно' if not getattr(chat, 'members_count', None) else chat.members_count}"
        )
        await message.answer(text, parse_mode="HTML")
    
    # Если это ответ на сообщение бота
    elif message.reply_to_message and message.reply_to_message.from_user.is_bot:
        bot_user = message.reply_to_message.from_user
        text = (
            f"🤖 <b>Информация о боте</b>\n\n"
            f"📝 Имя: {bot_user.first_name}\n"
            f"🆔 ID: <code>{bot_user.id}</code>\n"
            f"🔗 Username: @{bot_user.username if bot_user.username else 'отсутствует'}"
        )
        await message.answer(text, parse_mode="HTML")
    
    # Просто информация о пользователе
    elif not message.forward_from and not message.forward_from_chat:
        text = (
            f"👤 <b>Ваша информация</b>\n\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📝 Имя: {user.first_name}\n"
            f"📋 Фамилия: {user.last_name if user.last_name else 'отсутствует'}\n"
            f"🔗 Username: @{user.username if user.username else 'отсутствует'}\n"
            f"🤖 Бот: {'Да' if user.is_bot else 'Нет'}\n\n"
            f"💡 <i>Используйте кнопки меню для других функций</i>"
        )
        await message.answer(text, parse_mode="HTML")

# Запуск бота
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
