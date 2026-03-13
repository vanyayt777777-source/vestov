import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv("VEST_CREATOR_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Переменная окружения VEST_CREATOR_TOKEN не установлена!")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Словарь с примерами кодов
BOT_EXAMPLES = {
    "subscription": {
        "name": "📋 Обязательная подписка",
        "description": "Бот с проверкой подписки на канал",
        "code": """import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@your_channel")  # ID канала для проверки

if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Функция проверки подписки
async def check_subscription(user_id):
    try:
        user_channel_status = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return user_channel_status.status in ['member', 'administrator', 'creator']
    except:
        return False

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        keyboard = InlineKeyboardMarkup(row_width=1)
        menu_btn = InlineKeyboardButton("📋 Меню", callback_data="main_menu")
        keyboard.add(menu_btn)
        
        await message.answer(
            "✅ Спасибо за подписку! Добро пожаловать в бот.",
            reply_markup=keyboard
        )
    else:
        # Кнопка для подписки
        keyboard = InlineKeyboardMarkup(row_width=1)
        channel_url = f"https://t.me/{CHANNEL_ID.replace('@', '')}"
        subscribe_btn = InlineKeyboardButton("📢 Подписаться", url=channel_url)
        check_btn = InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")
        keyboard.add(subscribe_btn, check_btn)
        
        await message.answer(
            "❗️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=keyboard
        )

# Обработчик проверки подписки
@dp.callback_query_handler(Text(equals="check_sub"))
async def check_subscription_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        keyboard = InlineKeyboardMarkup(row_width=1)
        menu_btn = InlineKeyboardButton("📋 Меню", callback_data="main_menu")
        keyboard.add(menu_btn)
        
        await bot.edit_message_text(
            "✅ Спасибо за подписку! Добро пожаловать в бот.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=keyboard
        )
    else:
        await callback_query.answer("❌ Вы ещё не подписались на канал!", show_alert=True)

@dp.callback_query_handler(Text(equals="main_menu"))
async def show_main_menu(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("🔹 Функция 1", callback_data="func1")
    btn2 = InlineKeyboardButton("🔸 Функция 2", callback_data="func2")
    keyboard.add(btn1, btn2)
    
    await bot.edit_message_text(
        "📋 Главное меню:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)"""
    },
    
    "echo": {
        "name": "🔄 Эхо-бот",
        "description": "Простой бот, повторяющий сообщения пользователя",
        "code": """import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply(
        "👋 Привет! Я эхо-бот.\\n"
        "Отправь мне любое сообщение, и я повторю его."
    )

@dp.message_handler()
async def echo_message(message: types.Message):
    await message.answer(f"📢 Вы написали: {message.text}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)"""
    },
    
    "weather": {
        "name": "🌤 Погодный бот",
        "description": "Бот для получения погоды в любом городе",
        "code": """import os
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")  # Ключ с openweathermap.org

if not BOT_TOKEN or not WEATHER_API_KEY:
    raise ValueError("Не установлены переменные окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Я погодный бот.\\n"
        "🌍 Напиши название города, и я покажу текущую погоду."
    )

@dp.message_handler()
async def get_weather(message: types.Message):
    city = message.text.strip()
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                temp = data['main']['temp']
                feels_like = data['main']['feels_like']
                description = data['weather'][0]['description']
                humidity = data['main']['humidity']
                wind_speed = data['wind']['speed']
                
                weather_text = f"""
🌍 Город: {city}
🌡 Температура: {temp}°C
🤔 Ощущается как: {feels_like}°C
☁️ Погода: {description}
💧 Влажность: {humidity}%
💨 Ветер: {wind_speed} м/с
                """
                await message.answer(weather_text)
            else:
                await message.answer("❌ Город не найден. Проверьте название и попробуйте снова.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)"""
    },
    
    "poll": {
        "name": "📊 Бот для опросов",
        "description": "Бот для создания и проведения опросов",
        "code": """import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Состояния для создания опроса
class PollStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_options = State()

# Хранение опросов
polls = {}

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    create_btn = InlineKeyboardButton("📝 Создать опрос", callback_data="create_poll")
    list_btn = InlineKeyboardButton("📋 Мои опросы", callback_data="list_polls")
    keyboard.add(create_btn, list_btn)
    
    await message.answer(
        "👋 Привет! Я бот для создания опросов.\\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(Text(equals="create_poll"))
async def create_poll_start(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "📝 Введите вопрос для опроса:"
    )
    await PollStates.waiting_for_question.set()

@dp.message_handler(state=PollStates.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['question'] = message.text
        data['options'] = []
    
    await message.answer(
        "✏️ Теперь отправляйте варианты ответов по одному.\\n"
        "Когда закончите, отправьте команду /done"
    )
    await PollStates.waiting_for_options.set()

@dp.message_handler(state=PollStates.waiting_for_options)
async def process_option(message: types.Message, state: FSMContext):
    if message.text == '/done':
        async with state.proxy() as data:
            if len(data['options']) < 2:
                await message.answer("❌ Нужно минимум 2 варианта ответа!")
                return
            
            # Сохраняем опрос
            poll_id = len(polls) + 1
            polls[poll_id] = {
                'user_id': message.from_user.id,
                'question': data['question'],
                'options': data['options'],
                'votes': {opt: 0 for opt in data['options']}
            }
            
            # Создаем клавиатуру для голосования
            keyboard = InlineKeyboardMarkup(row_width=1)
            for opt in data['options']:
                btn = InlineKeyboardButton(opt, callback_data=f"vote_{poll_id}_{opt}")
                keyboard.add(btn)
            
            await message.answer(
                f"✅ Опрос создан!\\n\\n"
                f"❓ {data['question']}\\n\\n"
                f"Голосуйте:",
                reply_markup=keyboard
            )
            await state.finish()
    else:
        async with state.proxy() as data:
            data['options'].append(message.text)
            await message.answer(f"✅ Вариант добавлен! Отправьте следующий или /done")

@dp.callback_query_handler(Text(startswith="vote_"))
async def process_vote(callback_query: types.CallbackQuery):
    _, poll_id, option = callback_query.data.split('_', 2)
    poll_id = int(poll_id)
    
    if poll_id in polls:
        polls[poll_id]['votes'][option] += 1
        
        # Показываем результаты
        results = "\\n".join([f"{opt}: {count} голосов" for opt, count in polls[poll_id]['votes'].items()])
        await callback_query.answer("✅ Голос учтен!")
        await callback_query.message.answer(f"📊 Текущие результаты:\\n{results}")
    else:
        await callback_query.answer("❌ Опрос не найден!")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)"""
    },
    
    "reminder": {
        "name": "⏰ Бот-напоминалка",
        "description": "Бот для создания напоминаний",
        "code": """import os
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Хранилище напоминаний
reminders = {}

# Состояния
class ReminderStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_time = State()

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот-напоминалка.\\n"
        "Команды:\\n"
        "/remind - создать напоминание\\n"
        "/myreminders - мои напоминания"
    )

@dp.message_handler(commands=['remind'])
async def remind_command(message: types.Message):
    await message.answer("📝 Что напомнить?")
    await ReminderStates.waiting_for_text.set()

@dp.message_handler(state=ReminderStates.waiting_for_text)
async def process_reminder_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text
    
    await message.answer(
        "⏰ Через сколько минут напомнить?\\n"
        "(отправьте число)"
    )
    await ReminderStates.waiting_for_time.set()

@dp.message_handler(state=ReminderStates.waiting_for_time)
async def process_reminder_time(message: types.Message, state: FSMContext):
    try:
        minutes = int(message.text)
        if minutes <= 0:
            await message.answer("❌ Введите положительное число!")
            return
        
        async with state.proxy() as data:
            reminder_time = datetime.now() + timedelta(minutes=minutes)
            user_id = message.from_user.id
            
            if user_id not in reminders:
                reminders[user_id] = []
            
            reminder_id = len(reminders[user_id])
            reminders[user_id].append({
                'id': reminder_id,
                'text': data['text'],
                'time': reminder_time
            })
            
            await message.answer(
                f"✅ Напоминание создано!\\n"
                f"Текст: {data['text']}\\n"
                f"Время: {reminder_time.strftime('%H:%M %d.%m.%Y')}"
            )
            
            # Запускаем задачу напоминания
            asyncio.create_task(send_reminder(user_id, reminder_id, data['text'], minutes))
        
        await state.finish()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число!")

async def send_reminder(user_id, reminder_id, text, minutes):
    await asyncio.sleep(minutes * 60)
    await bot.send_message(
        user_id,
        f"⏰ НАПОМИНАНИЕ!\\n\\n{text}"
    )

@dp.message_handler(commands=['myreminders'])
async def list_reminders(message: types.Message):
    user_id = message.from_user.id
    if user_id in reminders and reminders[user_id]:
        text = "📋 Ваши напоминания:\\n\\n"
        for rem in reminders[user_id]:
            text += f"• {rem['text']} - {rem['time'].strftime('%H:%M %d.%m.%Y')}\\n"
        await message.answer(text)
    else:
        await message.answer("У вас нет активных напоминаний.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)"""
    }
}

# Главное меню
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    for key, example in BOT_EXAMPLES.items():
        btn = InlineKeyboardButton(example["name"], callback_data=f"example_{key}")
        keyboard.add(btn)
    
    await message.answer(
        "👋 Добро пожаловать в <b>Vest Creator</b>!\n\n"
        "Я предоставляю готовые исходные коды для Telegram ботов.\n"
        "Выберите интересующий вас пример:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# Обработчик выбора примера
@dp.callback_query_handler(Text(startswith="example_"))
async def show_example(callback_query: types.CallbackQuery):
    example_key = callback_query.data.replace("example_", "")
    example = BOT_EXAMPLES.get(example_key)
    
    if example:
        keyboard = InlineKeyboardMarkup(row_width=2)
        get_code_btn = InlineKeyboardButton("📄 Получить код", callback_data=f"code_{example_key}")
        back_btn = InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
        keyboard.add(get_code_btn, back_btn)
        
        await bot.edit_message_text(
            f"<b>{example['name']}</b>\n\n"
            f"{example['description']}\n\n"
            f"Нажмите «Получить код» для просмотра исходного кода.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode="HTML",
            reply_markup=keyboard
        )

# Обработчик получения кода
@dp.callback_query_handler(Text(startswith="code_"))
async def get_code(callback_query: types.CallbackQuery):
    example_key = callback_query.data.replace("code_", "")
    example = BOT_EXAMPLES.get(example_key)
    
    if example:
        keyboard = InlineKeyboardMarkup(row_width=1)
        back_btn = InlineKeyboardButton("◀️ Назад к описанию", callback_data=f"example_{example_key}")
        menu_btn = InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")
        keyboard.add(back_btn, menu_btn)
        
        # Разбиваем код на части, если он слишком длинный
        code = example["code"]
        if len(code) > 4000:
            # Отправляем код частями
            await bot.send_message(
                callback_query.message.chat.id,
                f"<b>Код для {example['name']}:</b>\n\n"
                f"<pre><code class='language-python'>{code[:3500]}</code></pre>",
                parse_mode="HTML"
            )
            await bot.send_message(
                callback_query.message.chat.id,
                f"<pre><code class='language-python'>{code[3500:]}</code></pre>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id
            )
        else:
            await bot.edit_message_text(
                f"<b>Код для {example['name']}:</b>\n\n"
                f"<pre><code class='language-python'>{code}</code></pre>",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode="HTML",
                reply_markup=keyboard
            )

# Обработчик возврата в меню
@dp.callback_query_handler(Text(equals="back_to_menu"))
async def back_to_menu(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    for key, example in BOT_EXAMPLES.items():
        btn = InlineKeyboardButton(example["name"], callback_data=f"example_{key}")
        keyboard.add(btn)
    
    await bot.edit_message_text(
        "👋 Добро пожаловать в <b>Vest Creator</b>!\n\n"
        "Я предоставляю готовые исходные коды для Telegram ботов.\n"
        "Выберите интересующий вас пример:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode="HTML",
        reply_markup=keyboard
    )

# Обработчик команды /help
@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await message.answer(
        "🔍 <b>Помощь по боту Vest Creator</b>\n\n"
        "Команды:\n"
        "/start - Запустить бота и показать меню\n"
        "/help - Показать эту справку\n\n"
        "Бот предоставляет готовые исходные коды для различных Telegram ботов.\n"
        "Просто выберите нужный пример и получите код!"
    )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
