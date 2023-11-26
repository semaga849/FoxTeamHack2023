from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import types
from database import cursor, connect
from dispatcher import dp, bot


class Registration(StatesGroup):
    name = State()


@dp.message_handler(commands=['reg'], chat_type='private')
async def reg(message: types.Message):
    cursor.execute(f"SELECT * FROM users WHERE tg_id={message.chat.id}")
    temp = cursor.fetchone()
    if temp:
        await message.answer("Вы уже зарегистрированы")
    else:
        await message.answer("Введите своё имя: ")
        await Registration.name.set()


@dp.message_handler(state=Registration.name)
async def take_name(message: types.Message, state: FSMContext):
    name = message.text
    await state.finish()
    try:
        cursor.execute(f"INSERT INTO users(name, tg_id, c_id, department, projects) VALUES('{name}',{message.chat.id}, -1002131916827, 'QA', 'Hackaton')")
        connect.commit()
        await message.answer("Вы успешно зарегистрировались")
    except:
        await message.answer("Что-то пошло не так...")
        connect.rollback()