from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import types
from database import cursor, connect
from dispatcher import dp, bot
import re


class Ed(StatesGroup):
    text = State()
    type = State()


class Task(StatesGroup):
    type = State()
    short_desc = State()
    desc = State()
    time = State()


@dp.message_handler(commands=['task'], chat_type='private')
async def create_task(message: types.Message):
    await message.answer("Напишите тип задачи: ")
    await Task.type.set()


@dp.message_handler(state=Task.type)
async def take_type(message: types.Message, state: FSMContext):
    await state.update_data(type=message.text)
    await message.answer("Напишите краткое содержание (title) задачи: ")
    await Task.next()


@dp.message_handler(state=Task.short_desc)
async def take_type(message: types.Message, state: FSMContext):
    await state.update_data(short_desc=message.text)
    await message.answer("Напишите описание задачи: ")
    await Task.next()


@dp.message_handler(state=Task.desc)
async def take_type(message: types.Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Напишите срок исполнения задачи: ")
    await Task.next()


@dp.message_handler(state=Task.time, chat_type='private')
async def srch(message: types.Message, state: FSMContext):
    try:
        await state.update_data(time=message.text)
        data = await state.get_data()
        await state.finish()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.inline_keyboard = [
        [types.InlineKeyboardButton('Принять задачу', callback_data='accepttask')],
        [types.InlineKeyboardButton('Редактировать задачу', callback_data='edittask')],
        [types.InlineKeyboardButton('Отклонить задачу', callback_data='declinetask')]
        ]
        await message.answer(f"Задача:\nТип задачи: {data['type']}\nКраткое содержание: {data['short_desc']}\nОписание: {data['desc']}\nВремя на исполнение: {data['time']}", reply_markup=keyboard)
    except:
        await message.answer('Произошла ошибка')


@dp.callback_query_handler(lambda c: c.data.startswith('edittask'), chat_type='private')
async def edittask(callback: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.inline_keyboard = [
        [types.InlineKeyboardButton("Выберите параметр для изменения", callback_data="nothing")],
        [types.InlineKeyboardButton("Тип задачи", callback_data="taketext~Тип задачи")],
        [types.InlineKeyboardButton("Краткое содержание", callback_data="taketext~Краткое содержание")],
        [types.InlineKeyboardButton("Описание", callback_data="taketext~Описание")],
        [types.InlineKeyboardButton("Время на исполнение", callback_data="taketext~Время на Исполнение")],
        [types.InlineKeyboardButton("Завершить редактирование", callback_data="accepttask")]
    ]
    text = callback.message.text
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("taketext~"), chat_type='private')
async def ed(callback: types.CallbackQuery, state: FSMContext):
    text = callback.message.text
    id = callback.message.message_id
    await callback.message.edit_text("Введите "+callback.data.split("~")[1])
    await Ed.text.set()
    await state.update_data(text=text, type=callback.data.split("~")[1], id=id)


@dp.message_handler(state=Ed.text)
async def editt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    id = data['id']
    text = message.text
    pattern = r"Задача:\n(Тип задачи): (.*)\n(Краткое содержание): (.*)\n(Описание): (.*)\n(Время на исполнение): (.*)"
    match = re.match(pattern, data['text'])
    new_message = ""
    if match:
        t = match.group(2)
        ks = match.group(4)
        d = match.group(6)
        v = match.group(8)
        if data['type'] == "Тип задачи":
            t = text
        elif data['type'] == "Краткое содержание":
            ks = text
        elif data['type'] == "Описание":
            d = text
        else:
            v = text
        new_message = f"Задача:\nТип задачи: {t}\nКраткое содержание: {ks}\nОписание: {d}\nВремя на исполнение: {v}"
    await state.finish()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.inline_keyboard = [
        [types.InlineKeyboardButton('Принять задачу', callback_data='accepttask')],
        [types.InlineKeyboardButton('Редактировать задачу', callback_data='edittask')],
        [types.InlineKeyboardButton('Отклонить задачу', callback_data='declinetask')]
    ]
    try:
        await bot.edit_message_text(message_id=id, chat_id=message.chat.id, text=new_message, reply_markup=keyboard)
    except Exception as e:
        print(e)


@dp.callback_query_handler(lambda c: c.data.startswith('declinetask'), chat_type='private')
async def declinetask(callback: types.CallbackQuery):
    await callback.answer('Задача отменена')
    await callback.message.delete()


@dp.callback_query_handler(lambda c: c.data.startswith('accepttask'), chat_type='private')
async def accepttask(callback: types.CallbackQuery):
    text = callback.message.text
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.inline_keyboard = [
        [types.InlineKeyboardButton('Выбрать проект', callback_data='chooseproject')]
    ]
    await callback.message.edit_text(text + "\nСтатус задачи: TODO", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith('chooseproject'), chat_type='private')
async def chooseproject(callback: types.CallbackQuery):
    try:
        text = callback.message.text
        cursor.execute(f"SELECT c_id FROM users WHERE tg_id={callback.message.chat.id}")
        cid = cursor.fetchone()
        print(cid)
        cursor.execute(f"SELECT project FROM projects WHERE chat_id={cid[0]}")
        projects = cursor.fetchall()
        print(projects)
        projects_list = [project[0] for project in projects]
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = []
        for button in projects_list:
            buttons.append(types.InlineKeyboardButton(button, callback_data=f"acceptproject~{button}"))
        keyboard.add(*buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer("Что-то пошло не так...")


@dp.callback_query_handler(lambda c: c.data.startswith('acceptproject~'), chat_type='private')
async def completedtask(callback: types.CallbackQuery):
    try:
        cursor.execute(f"SELECT c_id FROM users WHERE tg_id={callback.message.chat.id}")
        cid = cursor.fetchone()
        cursor.execute(f"SELECT name, tg_id FROM users WHERE c_id={cid[0]} and projects='{callback.data.split('~')[1]}'")
        dp = cursor.fetchall()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = []
        buttons.append(types.InlineKeyboardButton('Выберите сотрудников, ответственных за задачу', callback_data='nothing'))
        for deps in dp:
            buttons.append(types.InlineKeyboardButton(deps[0], callback_data=f"addpersonal~{deps[1]}~{callback.data.split('~')[1]}"))
        buttons.append(types.InlineKeyboardButton("Отправить уведомления", callback_data=f'sn~{callback.data.split("~")[1]}'))
        keyboard.add(*buttons)
        text = callback.message.text
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer("Что-то пошло не так...")


@dp.callback_query_handler(lambda c: c.data.startswith('addpersonal~'), chat_type='private')
async def adddepartment(callback: types.CallbackQuery):
    try:
        cursor.execute(f"SELECT c_id FROM users WHERE tg_id={callback.message.chat.id}")
        cid = cursor.fetchone()
        cursor.execute(f"SELECT name, tg_id FROM users WHERE c_id={cid[0]} and projects='{callback.data.split('~')[2]}'")
        dp = cursor.fetchall()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = []
        buttons.append(types.InlineKeyboardButton('Выберите сотрудников, ответственных за задачу', callback_data='nothing'))
        tmp = callback.data.split("~")[1].split(",")
        for deps in dp:
            if str(deps[1]) not in tmp:
                buttons.append(types.InlineKeyboardButton(deps[0], callback_data=f"add_personal~{deps[1]},{callback.data.split('~')[1]}~{callback.data.split('~')[2]}"))
        already_deps = callback.data.split("~")[1]
        buttons.append(types.InlineKeyboardButton("Отправить уведомления", callback_data=f'send_notifications~{already_deps}'))
        keyboard.add(*buttons)
        text = callback.message.text
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer("Что-то пошло не так...")


@dp.callback_query_handler(lambda c: c.data.startswith('sendnotifications~'), chat_type='private')
async def sendnotifications(callback: types.CallbackQuery):
    try:
        text = callback.message.text
        departments = callback.data.split("~")[1].split(",")
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.inline_keyboard = [
            [types.InlineKeyboardButton('Принять', callback_data='accept_quest')]
        ]
        for deps in departments:
            await bot.send_message(deps, "ПОСТУПИЛА ЗАДАЧА:\n" + text, reply_markup=keyboard)
        await callback.answer("Задача отправлена")
        await callback.message.edit_text(text)
    except:
        await bot.send_message("Что-то пошло не так...")


@dp.callback_query_handler(lambda c: c.data.startswith('sn~'), chat_type='private')
async def sn(callback: types.CallbackQuery):
    cursor.execute(f"SELECT c_id FROM users WHERE tg_id={callback.message.chat.id}")
    cid = cursor.fetchone()
    cursor.execute(f"SELECT tg_id FROM users WHERE c_id={cid[0]} AND projects='{callback.data.split('~')[1]}'")
    u = cursor.fetchall()
    users_list = [user[0] for user in u]
    text = callback.message.text
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.inline_keyboard = [
        [types.InlineKeyboardButton('Принять', callback_data='accept_quest')]
    ]
    for i in users_list:
        await bot.send_message(i, "ПОСТУПИЛА ЗАДАЧА:\n" + text, reply_markup=keyboard)
    await callback.answer("Задача отправлена")
    await callback.message.edit_text(text)