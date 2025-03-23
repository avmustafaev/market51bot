import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.loadenv import envi
from app.avito_parser import AvitoParser
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

bot = Bot(token=envi.token)
CHANNEL_ID = envi.chid


bot = Bot(
    token=envi.token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)  # Указываем parse_mode здесь
)
dp = Dispatcher()

class Form(StatesGroup):
    address = State()
    price = State()
    floor = State()
    area = State()
    rooms = State()
    name = State()
    phone = State()

# Состояния для команды /avito
class AvitoState(StatesGroup):
    url = State()  # Шаг 1: Ввод ссылки
    name = State()  # Шаг 2: Ввод имени
    phone = State()  # Шаг 3: Ввод телефона

def get_final_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Ошибок нет, отправить в канал", callback_data="send_to_channel")],
        [InlineKeyboardButton(text="🔄 Есть ошибки, заново", callback_data="restart")]
    ])

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Чтобы добавить карточку, нажмите МЕНЮ и выберите 'Создать новую карточку'.")

@dp.message(Command("new"))
async def new_command(message: types.Message, state: FSMContext):
    await state.clear()
    sent_message = await message.answer("📍 Введите адрес: ")
    await state.update_data(messages=[sent_message.message_id, message.message_id])
    await state.set_state(Form.address)
    

# Обработчик команды /avito
@dp.message(Command("avito"))
async def avito_command(message: types.Message, state: FSMContext):
    await state.clear()  # Очищаем состояние
    await message.answer("🔗 Введите ссылку на объявление Avito:")
    await state.set_state(AvitoState.url)  # Переходим к состоянию ввода ссылки

# Обработчик ввода ссылки с валидацией
@dp.message(AvitoState.url)
async def get_avito_url(message: types.Message, state: FSMContext):
    url = message.text.strip()  # Получаем ссылку

    # Валидация ссылки
    if not url.startswith(("https://www.avito.ru/", "http://www.avito.ru/")):
        await message.answer("❌ Ссылка должна вести на объявление Avito. Попробуйте ещё раз:")
        return  # Останавливаем выполнение, если ссылка невалидна

    await state.update_data(url=url)  # Сохраняем ссылку в состояние

    # Парсим объявление
    try:
        parser = AvitoParser()
        parsed_data = f'{parser.parse(url)}<a href="{url}">🔗 Переход на объявление</a>'
        await state.update_data(parsed_data=parsed_data)  # Сохраняем результат парсинга

        # Показываем результат и запрашиваем имя
        await message.answer(f"📄 Результат парсинга:\n\n{parsed_data}", disable_web_page_preview=True)
        await message.answer("😎 Введите имя собственника:")
        await state.set_state(AvitoState.name)  # Переходим к состоянию ввода имени
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке ссылки: {e}")
        await state.clear()  # Очищаем состояние в случае ошибки

# Обработчик ввода имени
@dp.message(AvitoState.name)
async def get_avito_name(message: types.Message, state: FSMContext):
    name = message.text.strip()  # Получаем имя
    await state.update_data(name=name)  # Сохраняем имя в состояние
    await message.answer("📞 Введите телефон собственника:")
    await state.set_state(AvitoState.phone)  # Переходим к состоянию ввода телефона

# Обработчик ввода телефона и отправки в канал
@dp.message(AvitoState.phone)
async def get_avito_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()  # Получаем телефон
    data = await state.get_data()  # Получаем все сохранённые данные
    
    # Формируем итоговое сообщение
    result = (
        f"{data.get('parsed_data', '')}"
        f"\n😎 Собственник: {data.get('name', 'Не указано')}\n"
        f"📞 Телефон: {phone}"
    )

    # Отправляем сообщение в канал
    await bot.send_message(CHANNEL_ID, result, parse_mode="HTML", disable_web_page_preview=True)
    await message.answer("✅ Объявление отправлено в канал!")
    await state.clear()  # Очищаем состояние    

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
    await process_step(message, state, Form.price, "💰 Введите цену:", "address")

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
    """Финальный шаг: сохраняет телефон перед удалением сообщений."""
    data = await state.get_data()
    messages = data.get("messages", [])

    await state.update_data(phone=message.text, user_id=message.from_user.id, username=message.from_user.username)
    
    messages.append(message.message_id)  # Добавляем последнее сообщение пользователя

    result = (f"✅ Ваша карточка:\n\n"
              f"📍 {data.get('address', 'Не указано')}\n"
              f"💰 {data.get('price', 'Не указано')} ₽\n"
              f"🪜 {data.get('floor', 'Не указано')}\n"
              f"📐 {data.get('area', 'Не указано')} м2\n"
              f"🚪 {data.get('rooms', 'Не указано')} комн.\n"
              f"👤 {data.get('name', 'Не указано')}\n"
              f"📞 {message.text}")  # Берём телефон из сообщения

    await delete_previous_messages(state, message.chat.id)

    sent_message = await message.answer(result, reply_markup=get_final_keyboard())
    await state.update_data(messages=[sent_message.message_id])

async def delete_previous_messages(state: FSMContext, chat_id: int):
    """Удаляет все предыдущие сообщения пользователя."""
    data = await state.get_data()
    messages_to_delete = data.get("messages", [])

    for msg_id in messages_to_delete:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass  

    await state.update_data(messages=[])

@dp.callback_query(F.data == "send_to_channel")
async def send_to_channel(callback: CallbackQuery, state: FSMContext):
    """Отправляет карточку в канал и удаляет сообщение с кнопками."""
    data = await state.get_data()

    if data.get("username"):
        user_link = f'<a href="https://t.me/{data["username"]}">Автор</a>'
    else:
        user_link = f'<a href="tg://user?id={data["user_id"]}">Автор</a>'

    post = (f"📍 <b>Адрес:</b> {data.get('address', 'Не указано')}\n"
            f"💰 <b>Цена:</b> {data.get('price', 'Не указано')} ₽\n"
            f"🪜 <b>Этаж/этажей:</b> {data.get('floor', 'Не указано')}\n"
            f"📐 <b>Площадь:</b> {data.get('area', 'Не указано')} м2\n"
            f"🚪 <b>Комнат:</b> #{data.get('rooms', 'Не указано')}комн\n"
            f"😎 <b>Собственник:</b> {data.get('name', 'Не указано')}\n"
            f"📞 <b>Телефон собственника:</b> {data.get('phone', 'Не указано')}\n\n"
            f"{user_link}")

    await bot.send_message(CHANNEL_ID, post, parse_mode="HTML")

    # Удаляем сообщение с кнопками
    messages = data.get("messages", [])
    if messages:
        try:
            await bot.delete_message(callback.message.chat.id, messages[-1])
        except Exception:
            pass

    await callback.answer("✅ Объявление отправлено в канал!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())