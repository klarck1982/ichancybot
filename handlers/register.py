from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from api.ichancy import api
from database.db import save_player, get_player

router = Router()

class RegisterStates(StatesGroup):
    email = State()
    password = State()
    username = State()

@router.message(F.text == "📝 تسجيل لاعب جديد")
async def register_start(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if player:
        await message.answer(
            f"⚠️ لديك حساب مسجل مسبقاً:\n"
            f"👤 اسم المستخدم: {player['username']}\n"
            f"🆔 Player ID: {player['player_id']}"
        )
        return
    await state.set_state(RegisterStates.email)
    await message.answer("📧 أدخل الإيميل الخاص باللاعب:")

@router.message(RegisterStates.email)
async def register_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text.strip())
    await state.set_state(RegisterStates.password)
    await message.answer("🔑 أدخل كلمة المرور:")

@router.message(RegisterStates.password)
async def register_password(message: types.Message, state: FSMContext):
    await state.update_data(password=message.text.strip())
    await state.set_state(RegisterStates.username)
    await message.answer("👤 أدخل اسم المستخدم (username):")

@router.message(RegisterStates.username)
async def register_done(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await message.answer("⏳ جاري إنشاء الحساب...")

    result = await api.register_player(
        email=data["email"],
        password=data["password"],
        login=message.text.strip()
    )

    if "error" in result:
        await message.answer(f"❌ فشل التسجيل:\n{result['error']}")
        return

    # محاولة استخراج player_id من الاستجابة
    player_id = (
        result.get("playerId") or
        result.get("id") or
        result.get("player", {}).get("id") or
        "غير متوفر"
    )

    if player_id != "غير متوفر":
        save_player(message.from_user.id, str(player_id), message.text.strip(), data["email"])

    await message.answer(
        f"✅ تم إنشاء الحساب بنجاح!\n\n"
        f"👤 اسم المستخدم: {message.text.strip()}\n"
        f"📧 الإيميل: {data['email']}\n"
        f"🆔 Player ID: {player_id}"
    )
