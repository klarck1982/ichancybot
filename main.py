await api._init_browser()
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.db import init_db
from handlers import register, balance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(register.router)
dp.include_router(balance.router)

def main_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📝 تسجيل لاعب جديد")],
            [types.KeyboardButton(text="💰 إيداع"), types.KeyboardButton(text="💸 سحب")],
            [types.KeyboardButton(text="💳 عرض الرصيد"), types.KeyboardButton(text="📊 سجل العمليات")],
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"👋 أهلاً {message.from_user.first_name}!\n\n"
        "🎰 مرحباً بك في بوت إدارة حسابات Ichancy\n\n"
        "اختر العملية من القائمة أدناه:",
        reply_markup=main_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 قائمة الأوامر:\n\n"
        "📝 تسجيل لاعب جديد — إنشاء حساب جديد\n"
        "💰 إيداع — إضافة رصيد\n"
        "💸 سحب — سحب رصيد\n"
        "💳 عرض الرصيد — الرصيد الحالي\n"
        "📊 سجل العمليات — آخر العمليات\n",
        reply_markup=main_keyboard()
    )

async def main():
    init_db()
    logger.info("البوت يعمل...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
