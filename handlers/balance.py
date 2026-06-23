from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from api.ichancy import api
from database.db import get_player, save_transaction, get_transactions

router = Router()

class DepositStates(StatesGroup):
    amount = State()

class WithdrawStates(StatesGroup):
    amount = State()

# ===== عرض الرصيد =====
@router.message(F.text == "💳 عرض الرصيد")
async def show_balance(message: types.Message):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ لا يوجد حساب مسجل. استخدم 📝 تسجيل لاعب جديد أولاً.")
        return

    await message.answer("⏳ جاري جلب الرصيد...")
    result = await api.get_balance(player["player_id"])

    if "error" in result:
        await message.answer(f"❌ خطأ: {result['error']}")
        return

    balance = result.get("balance") or result.get("amount") or result.get("data", {}).get("balance", "غير متوفر")

    await message.answer(
        f"💳 معلومات الحساب\n"
        f"{'─'*25}\n"
        f"👤 المستخدم: {player['username']}\n"
        f"🆔 Player ID: {player['player_id']}\n"
        f"💰 الرصيد: {balance}\n"
    )

# ===== إيداع =====
@router.message(F.text == "💰 إيداع")
async def deposit_start(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ لا يوجد حساب مسجل. استخدم 📝 تسجيل لاعب جديد أولاً.")
        return
    await state.set_state(DepositStates.amount)
    await message.answer(f"💰 أدخل مبلغ الإيداع للاعب {player['username']}:")

@router.message(DepositStates.amount)
async def deposit_done(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً أكبر من صفر.")
        return

    await state.clear()
    player = get_player(message.from_user.id)
    await message.answer(f"⏳ جاري إيداع {amount}...")

    result = await api.deposit(player["player_id"], amount)

    if "error" in result:
        save_transaction(message.from_user.id, player["player_id"], "deposit", amount, "failed")
        await message.answer(f"❌ فشل الإيداع:\n{result['error']}")
        return

    save_transaction(message.from_user.id, player["player_id"], "deposit", amount, "success")
    await message.answer(
        f"✅ تم الإيداع بنجاح!\n"
        f"💰 المبلغ: {amount}\n"
        f"👤 اللاعب: {player['username']}"
    )

# ===== سحب =====
@router.message(F.text == "💸 سحب")
async def withdraw_start(message: types.Message, state: FSMContext):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ لا يوجد حساب مسجل. استخدم 📝 تسجيل لاعب جديد أولاً.")
        return
    await state.set_state(WithdrawStates.amount)
    await message.answer(f"💸 أدخل مبلغ السحب للاعب {player['username']}:")

@router.message(WithdrawStates.amount)
async def withdraw_done(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً أكبر من صفر.")
        return

    await state.clear()
    player = get_player(message.from_user.id)
    await message.answer(f"⏳ جاري سحب {amount}...")

    result = await api.withdraw(player["player_id"], amount)

    if "error" in result:
        save_transaction(message.from_user.id, player["player_id"], "withdraw", amount, "failed")
        await message.answer(f"❌ فشل السحب:\n{result['error']}")
        return

    save_transaction(message.from_user.id, player["player_id"], "withdraw", amount, "success")
    await message.answer(
        f"✅ تم السحب بنجاح!\n"
        f"💸 المبلغ: {amount}\n"
        f"👤 اللاعب: {player['username']}"
    )

# ===== السجل =====
@router.message(F.text == "📊 سجل العمليات")
async def history(message: types.Message):
    player = get_player(message.from_user.id)
    if not player:
        await message.answer("❌ لا يوجد حساب مسجل.")
        return

    rows = get_transactions(message.from_user.id)
    if not rows:
        await message.answer("📭 لا توجد عمليات سابقة.")
        return

    text = "📊 آخر العمليات:\n" + "─"*25 + "\n"
    for t in rows:
        icon = "💰" if t[0] == "deposit" else "💸"
        status_icon = "✅" if t[2] == "success" else "❌"
        text += f"{icon} {t[0]} | {t[1]} | {status_icon} | {t[3][:16]}\n"

    await message.answer(text)
