import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === ДАННЫЕ ДЛЯ МАГАЗИНА ОДЕЖДЫ ===
CATEGORIES = ["👕 Футболки", "👖 Джинсы", "👟 Кроссовки", "🧥 Куртки"]

PRODUCTS = {
    "👕 Футболки": [
        {"name": "Black Oversize", "price": "1490 ₽", "desc": "Хлопок 100%, oversize fit", "photo": "https://picsum.photos/id/1015/400/400"},
        {"name": "White Classic", "price": "1290 ₽", "desc": "Базовая белая футболка", "photo": "https://picsum.photos/id/102/400/400"},
    ],
    "👖 Джинсы": [
        {"name": "Mom Jeans Blue", "price": "2990 ₽", "desc": "Высокая посадка, комфорт", "photo": "https://picsum.photos/id/201/400/400"},
        {"name": "Slim Black", "price": "2590 ₽", "desc": "Узкий крой", "photo": "https://picsum.photos/id/211/400/400"},
    ],
    "👟 Кроссовки": [
        {"name": "Nike Air Force", "price": "8990 ₽", "desc": "Классика 2026", "photo": "https://picsum.photos/id/301/400/400"},
    ],
    "🧥 Куртки": [
        {"name": "Denim Jacket", "price": "4490 ₽", "desc": "Джинсовая куртка", "photo": "https://picsum.photos/id/401/400/400"},
    ]
}

FAQ_DATA = {
    "❓ Как оформить заказ?": "Выберите товар в каталоге → нажмите 'Задать вопрос' → напишите размер и адрес.",
    "❓ Сколько доставка?": "По России — от 300 ₽ (СДЭК). Бесплатно от 5000 ₽.",
    "❓ Можно ли вернуть?": "Да, 14 дней. Без повреждений и с чеком.",
    "❓ Когда отправка?": "В день заказа, если до 18:00.",
}

# === СОСТОЯНИЯ (для тикетов) ===
class SupportStates(StatesGroup):
    waiting_for_ticket = State()

# === КЛАВИАТУРЫ ===
def main_keyboard():
    kb = [
        [KeyboardButton(text="🛍 Каталог")],
        [KeyboardButton(text="❓ FAQ"), KeyboardButton(text="📞 Поддержка")],
        [KeyboardButton(text="ℹ️ О магазине")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def category_keyboard():
    buttons = [[InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")] for cat in CATEGORIES]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === ХЕНДЛЕРЫ ===
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в StyleBot!\n\n"
        "Мы — магазин стильной одежды. Чем могу помочь?",
        reply_markup=main_keyboard()
    )

@dp.message(F.text == "🛍 Каталог")
async def catalog(message: types.Message):
    await message.answer("Выберите категорию:", reply_markup=category_keyboard())

@dp.callback_query(F.data.startswith("cat_"))
async def show_products(callback: types.CallbackQuery):
    category = callback.data[4:]
    products = PRODUCTS.get(category, [])
    text = f"📌 **{category}**\n\n"
    for p in products:
        text += f"• {p['name']} — {p['price']}\n"
    await callback.message.answer(text)
    await callback.answer()

    # Показываем каждый товар отдельно с фото
    for p in products:
        await callback.message.answer_photo(
            photo=p["photo"],
            caption=f"**{p['name']}**\n{p['desc']}\n💰 {p['price']}\n\nХотите спросить про размер/наличие?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="❓ Задать вопрос по товару", callback_data=f"ask_{p['name']}")
            ]])
        )

@dp.callback_query(F.data.startswith("ask_"))
async def ask_about_product(callback: types.CallbackQuery, state: FSMContext):
    product_name = callback.data[4:]
    await state.set_state(SupportStates.waiting_for_ticket)
    await callback.message.answer(
        f"✅ Вы спрашиваете про товар **{product_name}**.\n\n"
        "Опишите ваш вопрос (размер, цвет, наличие и т.д.). Я сразу передам его менеджеру."
    )
    await callback.answer()

@dp.message(F.text == "❓ FAQ")
async def faq(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=q, callback_data=f"faq_{q}")] for q in FAQ_DATA.keys()
    ])
    await message.answer("Выберите вопрос:", reply_markup=kb)

@dp.callback_query(F.data.startswith("faq_"))
async def show_faq_answer(callback: types.CallbackQuery):
    question = callback.data[4:]
    answer = FAQ_DATA.get(question, "Ответ скоро...")
    await callback.message.answer(f"**{question}**\n\n{answer}")
    await callback.answer()

@dp.message(F.text == "📞 Поддержка")
async def support(message: types.Message, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_ticket)
    await message.answer("📝 Опишите вашу проблему или вопрос. Я сразу передам его в поддержку.")

@dp.message(SupportStates.waiting_for_ticket)
async def save_ticket(message: types.Message, state: FSMContext):
    # Пересылаем сообщение админу
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    await bot.send_message(
        ADMIN_ID,
        f"🆘 Новый тикет от @{message.from_user.username or 'no_username'} (ID: {message.from_user.id})"
    )
    await message.answer("✅ Сообщение отправлено менеджеру! Ожидайте ответа в течение 5–15 минут.")
    await state.clear()

@dp.message(F.text == "ℹ️ О магазине")
async def about(message: types.Message):
    await message.answer(
        "🛍 StyleBot — магазин современной одежды 2026 года.\n\n"
        "Работаем 24/7 через бота.\n"
        "Все товары в наличии или под заказ."
    )

# === ЗАПУСК БОТА ===
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
