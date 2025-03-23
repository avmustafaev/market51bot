import asyncio
import contextlib
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.loadenv import envi

bot = Bot(token=envi.token)
CHANNEL_ID = envi.chid
dp = Dispatcher()

class Form(StatesGroup):
    address = State()
    district = State()
    property_type = State()
    price = State()
    floor = State()
    area = State()
    rooms = State()
    name = State()
    phone = State()

def get_final_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Ошибок нет, отправить в канал", callback_data="send_to_channel")],
        [InlineKeyboardButton(text="🔄 Есть ошибки, заново", callback_data="restart")]
    ])

districts = [
    "Автовокзал", "Академический", "Ботаника", "ВИЗ", "Вторчермет", "Втуз городок", 
    "Елизавет", "ЖБИ", "Завокзальный", "Заречный", "Пионерский", "Сортировка", 
    "Уралмаш", "Уткус", "Химмаш", "Центр", "Шарташ", "Широкая речка", "Эльмаш", "Юго запад"
]

property_types = ["Квартира", "Студия", "Апартаменты", "Дом", "Комната", "Общежитие"]

def get_inline_keyboard(options, callback_prefix):
    keyboard = []
    row = []
    
    for option in options:
        row.append(InlineKeyboardButton(text=option, callback_data=f"{callback_prefix}:{option}"))
        
        if len(row) == 2:  # После двух кнопок переносим на новую строку
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)  # Добавляем оставшиеся кнопки, если они есть
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Чтобы добавить карточку, нажмите МЕНЮ и выберите 'Создать новую карточку'.")

@dp.message(Command("new"))
async def new_command(message: types.Message, state: FSMContext):
    await state.clear()
    sent_message = await message.answer("📍 Введите адрес:")
    await state.update_data(messages=[sent_message.message_id, message.message_id])
    await state.set_state(Form.address)

@dp.callback_query(F.data == "restart")
async def restart_form(callback: CallbackQuery, state: FSMContext):
    await new_command(callback.message, state)

async def process_step(message: types.Message, state: FSMContext, next_state: State, prompt: str, key: str):
    data = await state.get_data()
    messages = data.get("messages", [])

    await state.update_data({key: message.text})
    messages.append(message.message_id)

    sent_message = await message.answer(prompt)
    messages.append(sent_message.message_id)

    await state.update_data(messages=messages)
    await state.set_state(next_state)

@dp.message(Form.address)
async def get_address(message: types.Message, state: FSMContext):
    await process_step(message, state, Form.district, "🌍 Выберите район:", "address")
    sent_message = await message.answer("Выберите район:", reply_markup=get_inline_keyboard(districts, "district"))
    data = await state.get_data()
    await state.update_data(messages=data["messages"] + [sent_message.message_id])

@dp.callback_query(F.data.startswith("district:"))
async def select_district(callback: CallbackQuery, state: FSMContext):
    district = callback.data.split(":")[1]
    await state.update_data(district=district)
    
    sent_message = await callback.message.answer("🏠 Выберите тип жилья:", reply_markup=get_inline_keyboard(property_types, "property_type"))
    
    data = await state.get_data()
    await state.update_data(messages=data["messages"] + [sent_message.message_id])

    await callback.answer()
    await state.set_state(Form.property_type)

@dp.callback_query(F.data.startswith("property_type:"))
async def select_property_type(callback: CallbackQuery, state: FSMContext):
    property_type = callback.data.split(":")[1]
    await state.update_data(property_type=property_type)

    sent_message = await callback.message.answer("💰 Введите цену:")
    data = await state.get_data()
    await state.update_data(messages=data["messages"] + [sent_message.message_id])

    await callback.answer()
    await state.set_state(Form.price)

@dp.message(Form.price)
async def get_price(message: types.Message, state: FSMContext):
    await process_step(message, state, Form.floor, "🪜 Введите этаж/этажей:", "price")

@dp.message(Form.floor)
async def get_floor(message: types.Message, state: FSMContext):
    await process_step(message, state, Form.area, "📐 Введите площадь:", "floor")

@dp.message(Form.area)
async def get_area(message: types.Message, state: FSMContext):
    await process_step(message, state, Form.rooms, "🚪 Введите количество комнат:", "area")

@dp.message(Form.rooms)
async def get_rooms(message: types.Message, state: FSMContext):
    await process_step(message, state, Form.name, "😎 Введите имя собственника:", "rooms")

@dp.message(Form.name)
async def get_name(message: types.Message, state: FSMContext):
    await process_step(message, state, Form.phone, "📞 Введите телефон собственника:", "name")

@dp.message(Form.phone)
async def get_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    messages = data.get("messages", [])

    await state.update_data(phone=message.text, user_id=message.from_user.id, username=message.from_user.username)
    messages.append(message.message_id)

    result = (f"✅ Ваша карточка:\n\n"
              f"📍 {data.get('address', 'Не указано')}\n"
              f"🏙 {data.get('district', 'Не указано')}\n"
              f"🏠 {data.get('property_type', 'Не указано')}\n"
              f"💰 {data.get('price', 'Не указано')} ₽\n"
              f"🪜 {data.get('floor', 'Не указано')}\n"
              f"📐 {data.get('area', 'Не указано')} м²\n"
              f"🚪 {data.get('rooms', 'Не указано')} комн.\n"
              f"😎 {data.get('name', 'Не указано')}\n"
              f"📞 {message.text}")

    await delete_previous_messages(state, message.chat.id)
    
    sent_message = await message.answer(result, reply_markup=get_final_keyboard())
    await state.update_data(messages=[sent_message.message_id])

async def delete_previous_messages(state: FSMContext, chat_id: int):
    data = await state.get_data()
    messages_to_delete = data.get("messages", [])

    for msg_id in messages_to_delete:
        with contextlib.suppress(Exception):
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    await state.update_data(messages=[])

@dp.callback_query(F.data == "send_to_channel")
async def send_to_channel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if data.get("username"):
        user_link = f'<a href="https://t.me/{data["username"]}">🔗 {data["username"]}</a>'
    else:
        user_link = f'<a href="tg://user?id={data["user_id"]}">🔗 {data["user_id"]}</a>'

    post = (f"📍 <b>{data.get('address', 'Не указано')}</b>\n"
            f"💰 <b>{data.get('price', 'Не указано')}₽</b>\n\n"
            f"🚪 #{data.get('rooms', 'Не указано')}комн\n"
            f"🏠 #{data.get('property_type', 'Не указано')}\n"
            f"🏙 #{data.get('district', 'Не указано')}\n"
            f"🪜 {data.get('floor', 'Не указано')}\n"
            f"📐 {data.get('area', 'Не указано')}м²\n\n"
            f"😎 {data.get('name', 'Не указано')}\n"
            f"📞 {data.get('phone', 'Не указано')}\n\n"
            f"<span class='tg-spoiler'>{user_link}</span>")

    await bot.send_message(CHANNEL_ID, post, parse_mode="HTML", disable_web_page_preview=True)
    await callback.message.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())