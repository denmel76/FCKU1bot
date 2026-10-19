mport aiosqlite

DB_NAME = "shop.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица товаров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                price INTEGER,
                photo_url TEXT
            )
        """)
        # Таблица корзины
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, product_id)
            )
        """)
        # Добавим тестовые товары, если таблица пуста
        cursor = await db.execute("SELECT COUNT(*) FROM products")
        count = (await cursor.fetchone())[0]
        if count == 0:
            await db.execute("INSERT INTO products (name, description, price, photo_url) VALUES (?, ?, ?, ?)",
                             ("Кружка", "Керамическая кружка 300мл", 500, "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=500"))
            await db.execute("INSERT INTO products (name, description, price, photo_url) VALUES (?, ?, ?, ?)",
                             ("Футболка", "Хлопковая футболка, размер M", 1500, "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500"))
            await db.execute("INSERT INTO products (name, description, price, photo_url) VALUES (?, ?, ?, ?)",
                             ("Блокнот", "Блокнот А5, 100 листов", 300, "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=500"))
            await db.commit()

async def get_products():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name, price, photo_url FROM products")
        return await cursor.fetchall()

async def get_product(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name, description, price, photo_url FROM products WHERE id = ?", (product_id,))
        return await cursor.fetchone()

async def add_to_cart(user_id, product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)
            ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = quantity + 1
        """, (user_id, product_id))
        await db.commit()

async def get_cart(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT p.id, p.name, p.price, c.quantity 
            FROM cart c JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = ?
        """, (user_id,))
        return await cursor.fetchall()

async def clear_cart(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()
4. bot.py
Основной файл с логикой (кнопки, корзина, оформление).

python
Copy
Download
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN, ADMIN_ID
from database import init_db, get_products, get_product, add_to_cart, get_cart, clear_cart

logging.basicConfig(level=logging.INFO)

class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ГЛАВНОЕ МЕНЮ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог товаров", callback_data="catalog")],
        [InlineKeyboardButton(text="🛒 Моя корзина", callback_data="cart")]
    ])
    await message.answer("Добро пожаловать в наш магазин!", reply_markup=keyboard)

# --- КАТАЛОГ ---
@dp.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    await callback.message.edit_text("Загрузка каталога...")
    products = await get_products()
    
    for prod in products:
        prod_id, name, price, photo_url = prod
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Купить за {price}₽", callback_data=f"buy_{prod_id}")]
        ])
        try:
            await bot.send_photo(callback.from_user.id, photo=photo_url, caption=f"*{name}*\nЦена: {price}₽", parse_mode="Markdown", reply_markup=keyboard)
        except:
            await bot.send_message(callback.from_user.id, text=f"*{name}*\nЦена: {price}₽", parse_mode="Markdown", reply_markup=keyboard)
            
    await callback.message.delete()

# --- ДОБАВЛЕНИЕ В КОРЗИНУ ---
@dp.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    await add_to_cart(callback.from_user.id, prod_id)
    await callback.answer("✅ Товар добавлен в корзину!")

# --- КОРЗИНА ---
@dp.callback_query(F.data == "cart")
async def show_cart(callback: CallbackQuery):
    cart_items = await get_cart(callback.from_user.id)
    
    if not cart_items:
        await callback.message.edit_text("Ваша корзина пуста.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="В меню", callback_data="back_to_menu")]]))
        return
        
    text = "🛒 *Ваша корзина:*\n\n"
    total = 0
    for item in cart_items:
        _, name, price, qty = item
        text += f"{name} x{qty} = {price * qty}₽\n"
        total += price * qty
        
    text += f"\n*Итого: {total}₽*"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="В меню", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог товаров", callback_data="catalog")],
        [InlineKeyboardButton(text="🛒 Моя корзина", callback_data="cart")]
    ])
    await callback.message.edit_text("Главное меню:", reply_markup=keyboard)

# --- ОФОРМЛЕНИЕ ЗАКАЗА ---
@dp.callback_query(F.data == "checkout")
async def checkout(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваше *Имя*:", parse_mode="Markdown")
    await state.set_state(OrderState.waiting_for_name)

@dp.message(OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите ваш *номер телефона*:", parse_mode="Markdown")
    await state.set_state(OrderState.waiting_for_phone)

@dp.message(OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    name = user_data['name']
    phone = message.text
    
    cart_items = await get_cart(message.from_user.id)
    total = sum(item[2] * item[3] for item in cart_items)
    
    order_text = f"📦 *НОВЫЙ ЗАКАЗ*\n\n👤 Имя: {name}\n📞 Телефон: {phone}\n🆔 ID клиента: {message.from_user.id}\n\n*Товары:*\n"
    for item in cart_items:
        _, prod_name, price, qty = item
        order_text += f"- {prod_name} x{qty} = {price * qty}₽\n"
    
    order_text += f"\n💰 *Итого: {total}₽*"
    
    # Отправка админу
    try:
        await bot.send_message(ADMIN_ID, order_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")
    
    await clear_cart(message.from_user.id)
    await message.answer("🎉 Спасибо! Ваш заказ оформлен. Менеджер свяжется с вами.")
    await state.clear()

# --- ЗАПУСК ---
async def main():
    await init_db()
    print("Магазин запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
