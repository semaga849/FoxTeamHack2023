import asyncio
import re
import time
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import types
from aiogram.types import ContentType, ChatType
from database import cursor, connect
from dispatcher import dp, bot
from aiogram.utils import executor
import logging
from registration import *
from private import *


logging.basicConfig(level=logging.INFO)


class Register(StatesGroup):
    name = State()


class Update(StatesGroup):
    name = State()


class Edit(StatesGroup):
    text = State()
    type = State()


class EKeywords(StatesGroup):
    text = State()


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ['/reg', '/task']
    keyboard.add(*buttons)
    await message.answer("Приветствуем вас в Fox notifications. Введите /reg для регистрации. "
                         "Если вы уже зарегистрированы - введите /task для создания задачи."
                         " Также вы можете воспользоваться специальными текстовыми кнопками", reply_markup=keyboard)


@dp.message_handler(commands=['keywords'])
async def keywords(message: types.Message):
    cursor.execute(f"SELECT keywords FROM dict WHERE c_id={message.chat.id}")
    temp = cursor.fetchone()
    if temp:
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.inline_keyboard = [
            [types.InlineKeyboardButton("Перезаписать", callback_data='~rewrite~')],
            [types.InlineKeyboardButton("Отмена", callback_data='~cancel~')]
        ]
        await message.answer(f"Текущий словарь: {temp[0]}")
    else:
        await message.answer("Компании с таким chat id не найдено")


@dp.callback_query_handler(lambda c: c.data.startswith("~cancel~"))
async def cancel(message: types.Message):
    await message.delete()


@dp.message_handler(commands=['register'])
async def register(message: types.Message):
    await message.answer("Введите название компании (чата).")
    await Register.name.set()


@dp.message_handler(state=Register.name)
async def complete(message: types.Message, state: FSMContext):
    try:
        cursor.execute(f"INSERT INTO company(chat_id, name) VALUES({message.chat.id}, {message.text})")
        connect.commit()
        cursor.execute(f"INSERT INTO dict(c_id) VALUES({message.chat.id})")
    except:
        connect.rollback()
    await state.finish()


@dp.message_handler(commands=['updateid'])
async def givename(message: types.Message):
    await message.answer("Введите название компании (чата).")
    await Update.name.set()


@dp.message_handler(state=Update.name)
async def updateid(message: types.Message, state: FSMContext):
    try:
        await state.finish()
        cursor.execute(f"SELECT chat_id FROM company WHERE LOWER(name)=LOWER('{message.text}')")
        temp = cursor.fetchone()
        if temp:
            cursor.execute(f"UPDATE company SET chat_id={message.chat.id} WHERE LOWER(name)=LOWER('{message.text}')")
            connect.commit()
            cursor.execute(f"UPDATE dict SET c_id={message.chat.id} WHERE c_id={temp[0]}")
            connect.commit()
            cursor.execute(f"UPDATE projects SET chat_id={message.chat.id} WHERE LOWER(name)=LOWER('{message.text}')")
            connect.commit()
            cursor.execute(f"UPDATE users SET c_id={message.chat.id} WHERE c_id={temp[0]}")
            await message.answer("Обновление завершено.")
        else:
            await message.answer("Такой компании не найдено")
    except:
        connect.rollback()
        await message.edit_text("Что-то пошло не так.")


@dp.callback_query_handler(lambda c: c.data.startswith('~rewrite~'))
async def rewrite(message: types.Message):
    await message.answer("Введите ключевые слова через запятую")
    await EKeywords.text.set()


@dp.message_handler(content_types='text')
async def search(message: types.Message):
    try:
        cursor.execute(f"SELECT keywords FROM dict WHERE c_id={message.chat.id}")
        kw = cursor.fetchone()
        keywords = kw[0].split(",")
        for word in keywords:
            word = word.replace(" ", "")
            if word.lower() in message.text.lower():
                message_text_lower = message.text.lower()
                index = message_text_lower.index(word.lower())+6
                if message.text[index:index+1] == ":":
                    index += 1
                message.text = message.text[index:]
                text = message.text.split(",")
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                keyboard.inline_keyboard = [
                [types.InlineKeyboardButton('Принять задачу', callback_data='accept_task')],
                [types.InlineKeyboardButton('Редактировать задачу', callback_data='edit_task')],
                [types.InlineKeyboardButton('Отклонить задачу', callback_data='decline_task')]
                ]
                await message.answer(f"Задача:\nТип задачи: {text[0]}\nКраткое содержание: {text[1]}\nОписание: {text[2]}\nВремя на исполнение: {text[3]}", reply_markup=keyboard)
                break
    except:
        await message.answer('К сожалению произошла ошибка вывода ключевых слов. Убедитесь, что вы добавляли слова в словарь и что обновили id чата. Если ошибка сохраняется - обратитесь к технической поддержке: +7XXXXXXXXXX')


@dp.callback_query_handler(lambda c: c.data.startswith('edit_task'))
async def edit_task(callback: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.inline_keyboard=[
        [types.InlineKeyboardButton("Выберите параметр для изменения", callback_data="nothing")],
        [types.InlineKeyboardButton("Тип задачи", callback_data="take_text~Тип задачи")],
        [types.InlineKeyboardButton("Краткое содержание", callback_data="take_text~Краткое содержание")],
        [types.InlineKeyboardButton("Описание", callback_data="take_text~Описание")],
        [types.InlineKeyboardButton("Время на исполнение", callback_data="take_text~Время на Исполнение")],
        [types.InlineKeyboardButton("Завершить редактирование", callback_data="accept_task")]
    ]
    text = callback.message.text
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("take_text~"))
async def editing(callback: types.CallbackQuery, state: FSMContext):
    text = callback.message.text
    id = callback.message.message_id
    await callback.message.edit_text("Введите "+callback.data.split("~")[1])
    await Edit.text.set()
    await state.update_data(text=text, type=callback.data.split("~")[1], id=id)


@dp.message_handler(state=Edit.text)
async def edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    id = data['id']
    text = message.text
    pattern = r"Задача:\n(Тип задачи):  (.*)\n(Краткое содержание):  (.*)\n(Описание):  (.*)\n(Время на исполнение):  (.*)"
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
        new_message = f"Задача:\nТип задачи:  {t}\nКраткое содержание:  {ks}\nОписание:  {d}\nВремя на исполнение:  {v}"
    await state.finish()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.inline_keyboard = [
        [types.InlineKeyboardButton('Принять задачу', callback_data='accept_task')],
        [types.InlineKeyboardButton('Редактировать задачу', callback_data='edit_task')],
        [types.InlineKeyboardButton('Отклонить задачу', callback_data='decline_task')]
    ]
    try:
        await bot.edit_message_text(message_id=id, chat_id=message.chat.id, text=new_message, reply_markup=keyboard)
    except Exception as e:
        print(e)


@dp.callback_query_handler(lambda c: c.data.startswith('decline_task'))
async def decline_task(callback: types.CallbackQuery):
    await callback.answer('Задача отменена')
    await callback.message.delete()


@dp.callback_query_handler(lambda c: c.data.startswith('accept_task'))
async def accept_task(callback: types.CallbackQuery):
    text = callback.message.text
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.inline_keyboard = [
        [types.InlineKeyboardButton('Выбрать проект', callback_data='choose_project')]
    ]
    await callback.message.edit_text(text + "\nСтатус задачи: TODO", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith('choose_project'))
async def choose_project(callback: types.CallbackQuery):
    try:
        text = callback.message.text
        cursor.execute(f"SELECT project FROM projects WHERE chat_id={callback.message.chat.id}")
        projects = cursor.fetchall()
        projects_list = [project[0] for project in projects]
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = []
        for button in projects_list:
            buttons.append(types.InlineKeyboardButton(button, callback_data=f"accept_project~{button}"))
        keyboard.add(*buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer("Что-то пошло не так...")


@dp.callback_query_handler(lambda c: c.data.startswith('accept_project~'))
async def completed_task(callback: types.CallbackQuery):
    try:
        cursor.execute(f"SELECT name, tg_id FROM users WHERE c_id={callback.message.chat.id} and projects='{callback.data.split('~')[1]}'")
        dp = cursor.fetchall()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = []
        buttons.append(types.InlineKeyboardButton('Выберите сотрудников, ответственных за задачу', callback_data='nothing'))
        for deps in dp:
            buttons.append(types.InlineKeyboardButton(deps[0], callback_data=f"add_personal~{deps[1]}~{callback.data.split('~')[1]}"))
        buttons.append(types.InlineKeyboardButton("Отправить уведомления", callback_data=f's_n~{callback.data.split("~")[1]}'))
        keyboard.add(*buttons)
        text = callback.message.text
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer("Что-то пошло не так...")


@dp.callback_query_handler(lambda c: c.data.startswith('add_personal~'))
async def add_department(callback: types.CallbackQuery):
    try:
        cursor.execute(f"SELECT name, tg_id FROM users WHERE c_id={callback.message.chat.id} and projects='{callback.data.split('~')[2]}'")
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


@dp.callback_query_handler(lambda c: c.data.startswith('send_notifications~'))
async def send_notifications(callback: types.CallbackQuery):
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


@dp.callback_query_handler(lambda c: c.data.startswith('s_n~'))
async def s_n(callback: types.CallbackQuery):
    cursor.execute(f"SELECT tg_id FROM users WHERE c_id={callback.message.chat.id} AND projects='{callback.data.split('~')[1]}'")
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


@dp.callback_query_handler(lambda c: c.data.startswith('accept_quest'))
async def a_q(callback: types.CallbackQuery):
    text = callback.message.text
    await callback.message.edit_reply_markup()


@dp.message_handler(state=EKeywords.text)
async def ekw(message: types.Message, state: FSMContext):
    try:
        cursor.execute(f"UPDATE dict SET keywords='{message.text}' WHERE c_id={message.chat.id}")
        connect.commit()
        await message.answer("Словарь обновлён")
    except:
        await message.answer("Что-то пошло не так...")
        connect.rollback()
    await state.finish()


def main():
    try:
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        # Здесь можно добавить логирование ошибки
        print(f"Failed while getting updates: {str(e)}\nBot will restart in 60 seconds")
        time.sleep(60)
        main()


if __name__ == '__main__':
    main()
