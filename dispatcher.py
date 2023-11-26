from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
bot = Bot(token='Token')
dp = Dispatcher(bot, storage=MemoryStorage())
