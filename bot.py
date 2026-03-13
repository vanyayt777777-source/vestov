import asyncio
import logging
import os
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncpg
import aiohttp

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация - токен основного бота
MAIN_BOT_TOKEN = "8734213650:AAEs0LfHNozKi8eh-NhJe6YlAkdXFBIQp6I"
DATABASE_URL = "postgresql://bothost_db_fc8cb8af0d40:coj-IisOOc4i2S3U-xhYMwTThKu_uIuu5OEDONacgO0@node1.pghost.ru:32826/bothost_db_fc8cb8af0d40"

logger.info("✅ Токен основного бота загружен")

# Состояния для создания бота
class CreateBotStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_bot_name = State()
    waiting_for_admin_id = State()
    waiting_for_crypto_api = State()

# Состояния для созданных ботов
class ShopStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_product_name = State()
    waiting_for_product_price = State()
    waiting_for_product_content = State()
    waiting_for_broadcast = State()

# Инициализация основного бота
main_bot = Bot(token=MAIN_BOT_TOKEN)
storage = MemoryStorage()
main_dp = Dispatcher(main_bot, storage=storage)

# Инициализация БД
async def init_db():
    try:
        logger.info("Подключение к базе данных...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Таблица пользователей
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE,
                username TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица созданных ботов
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS created_bots (
                id SERIAL PRIMARY KEY,
                bot_token TEXT UNIQUE,
                bot_name TEXT,
                bot_username TEXT,
                admin_id BIGINT,
                crypto_api TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                created_by BIGINT
            )
        ''')
        
        # Таблица товаров
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS shop_products (
                id SERIAL PRIMARY KEY,
                bot_token TEXT,
                name TEXT,
                price_usdt FLOAT,
                content TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица покупок
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS shop_purchases (
                id SERIAL PRIMARY KEY,
                bot_token TEXT,
                user_id BIGINT,
                username TEXT,
                product_name TEXT,
                invoice_id TEXT,
                amount FLOAT,
                status TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица настроек
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS shop_settings (
                bot_token TEXT PRIMARY KEY,
                channel_url TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        await conn.close()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise

# Класс для работы с Crypto Bot API
class CryptoBotAPI:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = "https://pay.crypt.bot/api"
    
    async def create_invoice(self, amount, description=""):
        url = f"{self.base_url}/createInvoice"
        headers = {
            "Crypto-Pay-API-Token": self.api_token,
            "Content-Type": "application/json"
        }
        data = {
            "asset": "USDT",
            "amount": str(amount),
            "description": description[:1024],
            "paid_btn_name": "viewItem",
            "paid_btn_url": "https://t.me/placeholder",
            "currency_type": "fiat",
            "fiat": "USD"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return result["result"]
        except Exception as e:
            logger.error(f"Ошибка при создании инвойса: {e}")
        return None
    
    async def check_invoice(self, invoice_id):
        url = f"{self.base_url}/getInvoices"
        headers = {"Crypto-Pay-API-Token": self.api_token}
        params = {"invoice_ids": str(invoice_id)}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok") and result.get("result", {}).get("items"):
                            return result["result"]["items"][0]
        except Exception as e:
            logger.error(f"Ошибка при проверке инвойса: {e}")
        return None
    
    async def get_balance(self):
        url = f"{self.base_url}/getBalance"
        headers = {"Crypto-Pay-API-Token": self.api_token}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return result["result"]
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}")
        return None

# Словарь для хранения запущенных ботов
active_bots = {}

# Функция для запуска созданного бота
async def run_shop_bot(bot_token, bot_name, admin_id, crypto_api):
    """Запускает отдельного бота-магазин"""
    if bot_token in active_bots:
        logger.info(f"Бот {bot_name} уже запущен")
        return
    
    bot = Bot(token=bot_token)
    dp = Dispatcher(bot, storage=MemoryStorage())
    crypto = CryptoBotAPI(crypto_api)
    
    active_bots[bot_token] = {"bot": bot, "dp": dp, "name": bot_name}
    
    @dp.message_handler(commands=['start'])
    async def shop_start(message: types.Message):
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🛍 Купить товар", callback_data="buy"),
            InlineKeyboardButton("👤 Профиль", callback_data="profile"),
            InlineKeyboardButton("ℹ️ О нас", callback_data="about")
        )
        
        if message.from_user.id == admin_id:
            keyboard.add(InlineKeyboardButton("⚙️ Админ панель", callback_data="admin"))
        
        await message.answer(f"Добро пожаловать в магазин {bot_name}!", reply_markup=keyboard)
    
    @dp.callback_query_handler(lambda c: c.data == "buy")
    async def shop_buy(callback_query: types.CallbackQuery):
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            products = await conn.fetch("SELECT * FROM shop_products WHERE bot_token = $1", bot_token)
            await conn.close()
            
            if not products:
                await callback_query.message.answer("🛒 Товаров пока нет")
                return
            
            keyboard = InlineKeyboardMarkup(row_width=1)
            for product in products:
                keyboard.add(InlineKeyboardButton(
                    f"{product['name']} - {product['price_usdt']} USDT",
                    callback_data=f"product_{product['id']}"
                ))
            
            keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
            await callback_query.message.answer("Выберите товар:", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback_query.message.answer("❌ Произошла ошибка")
    
    @dp.callback_query_handler(lambda c: c.data.startswith("product_"))
    async def shop_select_product(callback_query: types.CallbackQuery):
        try:
            product_id = int(callback_query.data.split("_")[1])
            
            conn = await asyncpg.connect(DATABASE_URL)
            product = await conn.fetchrow("SELECT * FROM shop_products WHERE id = $1", product_id)
            await conn.close()
            
            if not product:
                await callback_query.message.answer("❌ Товар не найден")
                return
            
            invoice = await crypto.create_invoice(
                amount=product['price_usdt'],
                description=f"Покупка товара {product['name']}"
            )
            
            if invoice:
                conn = await asyncpg.connect(DATABASE_URL)
                await conn.execute(
                    """
                    INSERT INTO shop_purchases (bot_token, user_id, username, product_name, invoice_id, amount, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    bot_token,
                    callback_query.from_user.id,
                    callback_query.from_user.username or "NoUsername",
                    product['name'],
                    str(invoice['invoice_id']),
                    product['price_usdt'],
                    'pending'
                )
                await conn.close()
                
                amount_rub = product['price_usdt'] * 90
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(
                    InlineKeyboardButton("💳 Оплатить", url=invoice['pay_url']),
                    InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_{invoice['invoice_id']}_{product_id}"),
                    InlineKeyboardButton("🔙 Назад", callback_data="buy")
                )
                
                await callback_query.message.answer(
                    f"🛒 Товар: {product['name']}\n"
                    f"💰 Цена: {product['price_usdt']} USDT (~{amount_rub} руб)\n\n"
                    f"📝 Для оплаты нажмите кнопку 'Оплатить'\n"
                    f"После оплаты нажмите 'Проверить оплату'",
                    reply_markup=keyboard
                )
            else:
                await callback_query.message.answer("❌ Ошибка при создании счета")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback_query.message.answer("❌ Произошла ошибка")
    
    @dp.callback_query_handler(lambda c: c.data.startswith("check_"))
    async def shop_check_payment(callback_query: types.CallbackQuery):
        try:
            parts = callback_query.data.split("_")
            if len(parts) < 3:
                await callback_query.message.answer("❌ Неверный формат данных")
                return
                
            invoice_id = parts[1]
            product_id = int(parts[2])
            
            invoice_data = await crypto.check_invoice(invoice_id)
            
            if invoice_data and invoice_data.get('status') == 'paid':
                conn = await asyncpg.connect(DATABASE_URL)
                await conn.execute("UPDATE shop_purchases SET status = 'completed' WHERE invoice_id = $1", invoice_id)
                product = await conn.fetchrow("SELECT * FROM shop_products WHERE id = $1", product_id)
                await conn.close()
                
                if product:
                    await callback_query.message.answer(f"✅ Оплата получена!\n\n🎁 Ваш товар:\n{product['content']}")
                    
                    try:
                        await bot.send_message(
                            admin_id,
                            f"💰 Новая покупка!\n\nТовар: {product['name']}\nПокупатель: @{callback_query.from_user.username or 'NoUsername'}\nСумма: {product['price_usdt']} USDT"
                        )
                    except:
                        pass
            else:
                await callback_query.message.answer("❌ Оплата не найдена или не завершена")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback_query.message.answer("❌ Произошла ошибка")
    
    @dp.callback_query_handler(lambda c: c.data == "profile")
    async def shop_profile(callback_query: types.CallbackQuery):
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            purchases = await conn.fetch(
                "SELECT * FROM shop_purchases WHERE bot_token = $1 AND user_id = $2 AND status = 'completed' ORDER BY created_at DESC LIMIT 5",
                bot_token, callback_query.from_user.id
            )
            await conn.close()
            
            purchases_text = "\n".join([
                f"• {p['product_name']} - {p['amount']} USDT - {p['created_at'].strftime('%d.%m.%Y %H:%M')}"
                for p in purchases
            ]) if purchases else "Пока нет покупок"
            
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
            await callback_query.message.answer(
                f"👤 Профиль\n\n🆔 ID: {callback_query.from_user.id}\n📱 Username: @{callback_query.from_user.username or 'Не указан'}\n\n📦 Последние покупки:\n{purchases_text}",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback_query.message.answer("❌ Произошла ошибка")
    
    @dp.callback_query_handler(lambda c: c.data == "about")
    async def shop_about(callback_query: types.CallbackQuery):
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            settings = await conn.fetchrow("SELECT * FROM shop_settings WHERE bot_token = $1", bot_token)
            bot_info = await conn.fetchrow("SELECT * FROM created_bots WHERE bot_token = $1", bot_token)
            await conn.close()
            
            channel_url = settings['channel_url'] if settings and settings.get('channel_url') else "Не указан"
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
            
            await callback_query.message.answer(
                f"ℹ️ О нас\n\n🏪 Название: {bot_info['bot_name'] if bot_info else bot_name}\n📅 Дата создания: {bot_info['created_at'].strftime('%d.%m.%Y') if bot_info else 'Неизвестно'}\n📢 Канал: {channel_url}",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback_query.message.answer("❌ Произошла ошибка")
    
    @dp.callback_query_handler(lambda c: c.data == "back_to_menu")
    async def shop_back_to_menu(callback_query: types.CallbackQuery):
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🛍 Купить товар", callback_data="buy"),
            InlineKeyboardButton("👤 Профиль", callback_data="profile"),
            InlineKeyboardButton("ℹ️ О нас", callback_data="about")
        )
        
        if callback_query.from_user.id == admin_id:
            keyboard.add(InlineKeyboardButton("⚙️ Админ панель", callback_data="admin"))
        
        await callback_query.message.answer("Главное меню:", reply_markup=keyboard)
    
    @dp.callback_query_handler(lambda c: c.data == "admin")
    async def shop_admin(callback_query: types.CallbackQuery):
        if callback_query.from_user.id != admin_id:
            await callback_query.message.answer("❌ У вас нет доступа к админ панели")
            return
        
        balance = await crypto.get_balance()
        balance_text = ""
        if balance:
            usdt_balance = next((item for item in balance if item.get('currency_code') == 'USDT'), None)
            if usdt_balance:
                balance_text = f"\n💰 Баланс: {usdt_balance.get('available', '0')} USDT"
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product"),
            InlineKeyboardButton("📱 Изменить канал", callback_data="admin_change_channel"),
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
        )
        
        await callback_query.message.answer(f"⚙️ Админ панель{balance_text}", reply_markup=keyboard)
    
    @dp.callback_query_handler(lambda c: c.data == "admin_stats")
    async def shop_admin_stats(callback_query: types.CallbackQuery):
        if callback_query.from_user.id != admin_id:
            return
        
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            total_products = await conn.fetchval("SELECT COUNT(*) FROM shop_products WHERE bot_token = $1", bot_token)
            total_purchases = await conn.fetchval("SELECT COUNT(*) FROM shop_purchases WHERE bot_token = $1 AND status = 'completed'", bot_token)
            total_revenue = await conn.fetchval("SELECT COALESCE(SUM(amount), 0) FROM shop_purchases WHERE bot_token = $1 AND status = 'completed'", bot_token)
            unique_users = await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM shop_purchases WHERE bot_token = $1 AND status = 'completed'", bot_token)
            recent_purchases = await conn.fetch("SELECT * FROM shop_purchases WHERE bot_token = $1 AND status = 'completed' ORDER BY created_at DESC LIMIT 5", bot_token)
            await conn.close()
            
            purchases_text = "\n".join([
                f"• {p['product_name']} - @{p['username']} - {p['amount']} USDT"
                for p in recent_purchases
            ]) if recent_purchases else "Нет покупок"
            
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Назад", callback_data="admin"))
            await callback_query.message.answer(
                f"📊 Статистика магазина\n\n📦 Товаров: {total_products}\n💰 Продаж: {total_purchases}\n💵 Выручка: {total_revenue} USDT\n👥 Покупателей: {unique_users}\n\n📋 Последние покупки:\n{purchases_text}",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback_query.message.answer("❌ Произошла ошибка")
    
    @dp.callback_query_handler(lambda c: c.data == "admin_add_product")
    async def shop_admin_add_product(callback_query: types.CallbackQuery, state: FSMContext):
        if callback_query.from_user.id != admin_id:
            return
        
        await callback_query.message.answer("Введите название товара:")
        await ShopStates.waiting_for_product_name.set()
    
    @dp.message_handler(state=ShopStates.waiting_for_product_name)
    async def shop_process_product_name(message: types.Message, state: FSMContext):
        await state.update_data(product_name=message.text)
        await message.answer("Введите цену товара в USDT (например: 10.5):")
        await ShopStates.waiting_for_product_price.set()
    
    @dp.message_handler(state=ShopStates.waiting_for_product_price)
    async def shop_process_product_price(message: types.Message, state: FSMContext):
        try:
            price = float(message.text.replace(',', '.'))
            if price <= 0:
                await message.answer("❌ Цена должна быть больше 0")
                return
            await state.update_data(product_price=price)
            await message.answer("Введите контент товара (то, что получит покупатель):")
            await ShopStates.waiting_for_product_content.set()
        except ValueError:
            await message.answer("❌ Неверный формат цены. Введите число")
    
    @dp.message_handler(state=ShopStates.waiting_for_product_content)
    async def shop_process_product_content(message: types.Message, state: FSMContext):
        try:
            data = await state.get_data()
            
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                "INSERT INTO shop_products (bot_token, name, price_usdt, content) VALUES ($1, $2, $3, $4)",
                bot_token, data['product_name'], data['product_price'], message.text
            )
            await conn.close()
            
            await state.finish()
            await message.answer("✅ Товар успешно добавлен!")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await message.answer("❌ Ошибка при добавлении товара")
            await state.finish()
    
    @dp.callback_query_handler(lambda c: c.data == "admin_change_channel")
    async def shop_admin_change_channel(callback_query: types.CallbackQuery, state: FSMContext):
        if callback_query.from_user.id != admin_id:
            return
        
        await callback_query.message.answer("Введите ссылку на канал (например: https://t.me/channel):")
        await ShopStates.waiting_for_channel.set()
    
    @dp.message_handler(state=ShopStates.waiting_for_channel)
    async def shop_process_channel(message: types.Message, state: FSMContext):
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute(
                """
                INSERT INTO shop_settings (bot_token, channel_url) VALUES ($1, $2)
                ON CONFLICT (bot_token) DO UPDATE SET channel_url = $2
                """,
                bot_token, message.text
            )
            await conn.close()
            
            await state.finish()
            await message.answer("✅ Канал успешно обновлен!")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await message.answer("❌ Ошибка при обновлении канала")
            await state.finish()
    
    @dp.callback_query_handler(lambda c: c.data == "admin_broadcast")
    async def shop_admin_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
        if callback_query.from_user.id != admin_id:
            return
        
        await callback_query.message.answer("Введите сообщение для рассылки:")
        await ShopStates.waiting_for_broadcast.set()
    
    @dp.message_handler(state=ShopStates.waiting_for_broadcast)
    async def shop_process_broadcast(message: types.Message, state: FSMContext):
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            users = await conn.fetch("SELECT DISTINCT user_id FROM shop_purchases WHERE bot_token = $1", bot_token)
            await conn.close()
            
            if not users:
                await message.answer("❌ Нет пользователей для рассылки")
                await state.finish()
                return
            
            sent = 0
            for user in users:
                try:
                    await bot.send_message(user['user_id'], f"📢 Рассылка:\n\n{message.text}")
                    sent += 1
                    await asyncio.sleep(0.05)
                except:
                    pass
            
            await state.finish()
            await message.answer(f"✅ Рассылка завершена. Отправлено {sent} пользователям.")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await message.answer("❌ Ошибка при рассылке")
            await state.finish()
    
    try:
        logger.info(f"✅ Запущен бот: {bot_name}")
        await dp.start_polling()
    except Exception as e:
        logger.error(f"❌ Ошибка в боте {bot_name}: {e}")
    finally:
        await bot.session.close()
        if bot_token in active_bots:
            del active_bots[bot_token]

# Обработчики основного бота
@main_dp.message_handler(commands=['start'])
async def main_start(message: types.Message):
    # Сохраняем пользователя
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute(
            """
            INSERT INTO users (telegram_id, username) VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO UPDATE SET username = $2
            """,
            message.from_user.id, message.from_user.username or "NoUsername"
        )
        await conn.close()
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя: {e}")
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Создать бота", callback_data="create_bot"),
        InlineKeyboardButton("📋 Мои боты", callback_data="my_bots"),
        InlineKeyboardButton("📊 Статистика", callback_data="main_stats")
    )
    
    await message.answer(
        "🤖 Добро пожаловать в VEST CREATOR!\n\n"
        "Здесь вы можете создать своего бота-магазин с приемом платежей через Crypto Bot.",
        reply_markup=keyboard
    )

@main_dp.callback_query_handler(lambda c: c.data == "create_bot")
async def process_create_bot(callback_query: types.CallbackQuery):
    await callback_query.message.answer(
        "🔧 Создание нового бота\n\n"
        "Шаг 1 из 4: Отправьте токен вашего бота (получить у @BotFather)"
    )
    await CreateBotStates.waiting_for_token.set()

@main_dp.message_handler(state=CreateBotStates.waiting_for_token)
async def process_bot_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    
    try:
        test_bot = Bot(token=token)
        me = await test_bot.get_me()
        await test_bot.session.close()
        
        await state.update_data(bot_token=token, bot_username=me.username)
        await message.answer(
            f"✅ Бот @{me.username} успешно проверен!\n\n"
            "Шаг 2 из 4: Введите название магазина"
        )
        await CreateBotStates.waiting_for_bot_name.set()
    except Exception as e:
        await message.answer(f"❌ Ошибка: неверный токен")

@main_dp.message_handler(state=CreateBotStates.waiting_for_bot_name)
async def process_bot_name(message: types.Message, state: FSMContext):
    await state.update_data(bot_name=message.text)
    await message.answer(
        "Шаг 3 из 4: Введите ваш Telegram ID (администратора магазина)"
    )
    await CreateBotStates.waiting_for_admin_id.set()

@main_dp.message_handler(state=CreateBotStates.waiting_for_admin_id)
async def process_admin_id(message: types.Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
        await state.update_data(admin_id=admin_id)
        await message.answer(
            "Шаг 4 из 4: Введите ваш Crypto Bot API токен\n"
            "Получить можно у @CryptoBot"
        )
        await CreateBotStates.waiting_for_crypto_api.set()
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число:")

@main_dp.message_handler(state=CreateBotStates.waiting_for_crypto_api)
async def process_crypto_api(message: types.Message, state: FSMContext):
    data = await state.get_data()
    crypto_api = message.text.strip()
    
    # Проверяем Crypto Bot API
    try:
        test_crypto = CryptoBotAPI(crypto_api)
        balance = await test_crypto.get_balance()
        if balance is None:
            await message.answer("❌ Неверный Crypto Bot API токен")
            return
    except Exception as e:
        await message.answer(f"❌ Ошибка при проверке API")
        return
    
    # Сохраняем бота
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            """
            INSERT INTO created_bots (bot_token, bot_name, bot_username, admin_id, crypto_api, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            data['bot_token'], data['bot_name'], data['bot_username'],
            data['admin_id'], crypto_api, message.from_user.id
        )
        
        await state.finish()
        
        # Запускаем бота
        asyncio.create_task(
            run_shop_bot(
                data['bot_token'], data['bot_name'],
                data['admin_id'], crypto_api
            )
        )
        
        await message.answer(
            f"✅ Бот успешно создан и запущен!\n\n"
            f"📊 Название: {data['bot_name']}\n"
            f"🤖 Бот: @{data['bot_username']}\n"
            f"👑 Админ ID: {data['admin_id']}\n\n"
            f"Бот уже работает! Напишите /start в созданном боте."
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при сохранении")
    finally:
        await conn.close()

@main_dp.callback_query_handler(lambda c: c.data == "my_bots")
async def process_my_bots(callback_query: types.CallbackQuery):
    conn = await asyncpg.connect(DATABASE_URL)
    bots = await conn.fetch(
        "SELECT * FROM created_bots WHERE created_by = $1 ORDER BY created_at DESC",
        callback_query.from_user.id
    )
    await conn.close()
    
    if not bots:
        await callback_query.message.answer("У вас пока нет созданных ботов")
        return
    
    text = "📋 Ваши боты:\n\n"
    for bot in bots:
        status = "✅ Активен" if bot['is_active'] else "❌ Неактивен"
        text += f"🤖 {bot['bot_name']}\n"
        text += f"📅 Создан: {bot['created_at'].strftime('%d.%m.%Y')}\n"
        text += f"📊 Статус: {status}\n\n"
    
    await callback_query.message.answer(text)

@main_dp.callback_query_handler(lambda c: c.data == "main_stats")
async def process_main_stats(callback_query: types.CallbackQuery):
    conn = await asyncpg.connect(DATABASE_URL)
    
    total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
    total_bots = await conn.fetchval("SELECT COUNT(*) FROM created_bots")
    active_bots_count = await conn.fetchval("SELECT COUNT(*) FROM created_bots WHERE is_active = TRUE")
    total_purchases = await conn.fetchval("SELECT COUNT(*) FROM shop_purchases WHERE status = 'completed'")
    
    await conn.close()
    
    await callback_query.message.answer(
        f"📊 Общая статистика VEST CREATOR\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🤖 Всего ботов: {total_bots}\n"
        f"✅ Активных ботов: {active_bots_count}\n"
        f"💰 Всего покупок: {total_purchases}"
    )

# Запуск всех ботов при старте
async def start_all_bots():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        bots = await conn.fetch("SELECT * FROM created_bots WHERE is_active = TRUE")
        await conn.close()
        
        for bot in bots:
            asyncio.create_task(
                run_shop_bot(
                    bot['bot_token'], bot['bot_name'],
                    bot['admin_id'], bot['crypto_api']
                )
            )
            logger.info(f"Запущен бот: {bot['bot_name']}")
    except Exception as e:
        logger.error(f"Ошибка при запуске ботов: {e}")

async def main():
    # Инициализируем БД
    await init_db()
    
    # Запускаем всех сохраненных ботов
    await start_all_bots()
    
    # Запускаем основного бота
    logger.info("🚀 Запуск основного бота VEST CREATOR")
    await main_dp.start_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
