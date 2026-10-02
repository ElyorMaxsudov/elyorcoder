from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.fsm.context import FSMContext
from database import (
    get_user,
    update_balance,
    create_payment,
    get_payment,
    update_payment_status,
    add_referral_earnings,
    get_setting
)
from keyboards.inline import (
    get_deposit_methods_keyboard,
    get_stars_deposit_keyboard,
    get_admin_payment_verify_keyboard,
    get_back_button
)
from keyboards.reply import get_cancel_menu, get_main_menu
from utils.states import DepositStates
from utils.formatters import format_uzs
from config import ADMIN_IDS, STAR_RATE_UZS, REFERRAL_PERCENT

router = Router()

@router.message(F.text == "💰 Balans to'ldirish")
async def show_deposit_methods(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    balance = user["balance"] if user else 0.0

    text = (
        f"💰 <b>Balansni to'ldirish</b>\n\n"
        f"💵 <b>Sizning balansingiz:</b> <b>{format_uzs(balance)}</b>\n\n"
        f"To'lov qilish uchun qulay usulni tanlang:"
    )
    await message.answer(text, reply_markup=get_deposit_methods_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "back_to_deposit_methods")
async def back_to_deposit_methods(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_user(callback.from_user.id)
    balance = user["balance"] if user else 0.0

    text = (
        f"💰 <b>Balansni to'ldirish</b>\n\n"
        f"💵 <b>Sizning balansingiz:</b> <b>{format_uzs(balance)}</b>\n\n"
        f"To'lov qilish uchun qulay usulni tanlang:"
    )
    await callback.message.edit_text(text, reply_markup=get_deposit_methods_keyboard(), parse_mode="HTML")
    await callback.answer()

# ==================== KARTA ORQALI TO'LOV ====================

@router.callback_query(F.data == "pay_card")
async def callback_pay_card(callback: CallbackQuery, state: FSMContext):
    min_dep = await get_setting("min_deposit", "5000")
    await state.set_state(DepositStates.waiting_for_amount)
    await callback.message.delete()
    await callback.message.answer(
        f"💳 <b>Karta orqali hisob to'ldirish</b>\n\n"
        f"Qancha mablag' (so'm) to'ldirmoqchisiz?\n"
        f"Minimal summa: <b>{format_uzs(float(min_dep))}</b>\n\n"
        f"<i>Iltimos, summani raqamda kiriting (masalan: 10000):</i>",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(DepositStates.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ To'lov bekor qilindi.", reply_markup=get_main_menu())
        return

    if not text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting (masalan: 10000 yoki 50000):")
        return

    amount = float(text)
    min_dep = float(await get_setting("min_deposit", "5000"))

    if amount < min_dep:
        await message.answer(f"⚠️ Minimal to'lov summasi — <b>{format_uzs(min_dep)}</b>. Qaytadan kiriting:", parse_mode="HTML")
        return

    await state.update_data(deposit_amount=amount)
    await state.set_state(DepositStates.waiting_for_receipt)

    card_num = await get_setting("card_number", "8600 0000 0000 0000")
    card_holder = await get_setting("card_holder", "SMM BOT ADMIN")

    instruction = (
        f"💳 <b>To'lov ma'lumotlari:</b>\n\n"
        f"• Karta raqami: <code>{card_num}</code>\n"
        f"• Karta egasi: <b>{card_holder}</b>\n"
        f"• To'lanadigan summa: <b>{format_uzs(amount)}</b>\n\n"
        f"⚠️ <b>Ko'rsatma:</b>\n"
        f"1. Yuqoridagi kartaga <b>{format_uzs(amount)}</b> o'tkazing.\n"
        f"2. To'lov chekini (skrinshot yoki PDF) ushbu botga yuboring.\n\n"
        f"<i>Chek yuborilgandan so'ng 5-15 daqiqa ichida hisobingizga mablag' tushadi.</i>"
    )
    await message.answer(instruction, reply_markup=get_cancel_menu(), parse_mode="HTML")

@router.message(DepositStates.waiting_for_receipt, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("deposit_amount", 0.0)
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    photo_id = message.photo[-1].file_id if message.photo else message.document.file_id

    # Bazaga yozish
    payment_id = await create_payment(
        user_id=user_id,
        amount=amount,
        method="CARD",
        receipt_photo_id=photo_id
    )

    await state.clear()
    await message.answer(
        "✅ <b>To'lov chekingiz qabul qilindi!</b>\n\n"
        "Admin tekshirib chiqqach, mablag' zudlik bilan balansingizga qo'shiladi.",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

    # Adminga yuborish
    admin_caption = (
        f"💳 <b>YANGI TO'LOV CHEKI #{payment_id}</b>\n\n"
        f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{user_name}</a>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💵 Summa: <b>{format_uzs(amount)}</b>\n"
        f"Usul: Karta o'tkazmasi\n\n"
        f"To'lovni tasdiqlaysizmi?"
    )

    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await message.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_id,
                    caption=admin_caption,
                    reply_markup=get_admin_payment_verify_keyboard(payment_id),
                    parse_mode="HTML"
                )
            else:
                await message.bot.send_document(
                    chat_id=admin_id,
                    document=photo_id,
                    caption=admin_caption,
                    reply_markup=get_admin_payment_verify_keyboard(payment_id),
                    parse_mode="HTML"
                )
        except Exception:
            pass

# ==================== TELEGRAM STARS ORQALI TO'LOV ====================

@router.message(F.text == "⭐ Telegram Stars")
@router.callback_query(F.data == "pay_stars")
async def show_stars_deposit(event: Message | CallbackQuery):
    text = (
        "⭐ <b>Telegram Stars orqali hisob to'ldirish</b>\n\n"
        f"⚡ <i>Telegram ilovasi orqali 1 soniyada avtomatik to'lov!</i>\n"
        f"💵 Kurs: <b>1 Star = {STAR_RATE_UZS} so'm</b>\n\n"
        "O'zingizga ma'qul paketni tanlang:"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=get_stars_deposit_keyboard(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_stars_deposit_keyboard(), parse_mode="HTML")

@router.callback_query(F.data.startswith("stars_dep_"))
async def process_stars_invoice(callback: CallbackQuery):
    stars_count = int(callback.data.split("_")[2])
    amount_uzs = stars_count * STAR_RATE_UZS
    user_id = callback.from_user.id

    prices = [LabeledPrice(label=f"{stars_count} Stars", amount=stars_count)]

    await callback.message.delete()
    await callback.message.answer_invoice(
        title=f"Balansni to'ldirish ({format_uzs(amount_uzs)})",
        description=f"Bot hisobingizga {format_uzs(amount_uzs)} qo'shiladi.",
        payload=f"stars_{user_id}_{amount_uzs}_{stars_count}",
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    sp = message.successful_payment
    payload = sp.invoice_payload
    # payload: stars_{user_id}_{amount_uzs}_{stars_count}
    parts = payload.split("_")
    user_id = int(parts[1])
    amount_uzs = float(parts[2])
    stars_count = int(parts[3])

    # 1. Foydalanuvchi hisobiga qo'shish
    await update_balance(user_id, amount_uzs)

    # 2. To'lovlar tarixiga yozish
    await create_payment(
        user_id=user_id,
        amount=amount_uzs,
        method="STARS",
        stars_charge_id=sp.telegram_payment_charge_id
    )

    # 3. Referal bonusini berish
    user = await get_user(user_id)
    if user and user.get("referrer_id"):
        ref_id = user["referrer_id"]
        ref_bonus = round((amount_uzs * REFERRAL_PERCENT) / 100.0, 2)
        if ref_bonus > 0:
            await add_referral_earnings(ref_id, ref_bonus)
            try:
                await message.bot.send_message(
                    ref_id,
                    f"🎉 <b>Referal bonusi!</b>\n\n"
                    f"Do'stingiz hisobini to'ldirdi va sizga <b>+{format_uzs(ref_bonus)}</b> bonus berildi!",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    await message.answer(
        f"🎉 <b>To'lovingiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"⭐ To'langan Stars: <b>{stars_count} ta</b>\n"
        f"💰 Balansingizga qo'shildi: <b>+{format_uzs(amount_uzs)}</b>\n\n"
        f"Endi bemalol '🚀 Xizmatlar' bo'limidan buyurtma berishingiz mumkin!",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

# ==================== ADMIN TO'LOV TASDIQLASH ====================

@router.callback_query(F.data.startswith("adm_pay_ok_"))
async def callback_admin_approve_payment(callback: CallbackQuery):
    payment_id = int(callback.data.split("_")[3])
    payment = await get_payment(payment_id)

    if not payment:
        await callback.answer("To'lov topilmadi.", show_alert=True)
        return

    if payment["status"] != "PENDING":
        await callback.answer("Bu to'lov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    user_id = payment["user_id"]
    amount = payment["amount"]

    # 1. Statusni yangilash
    await update_payment_status(payment_id, "APPROVED")

    # 2. Balansni to'ldirish
    await update_balance(user_id, amount)

    # 3. Referal bonusini berish
    user = await get_user(user_id)
    if user and user.get("referrer_id"):
        ref_id = user["referrer_id"]
        ref_bonus = round((amount * REFERRAL_PERCENT) / 100.0, 2)
        if ref_bonus > 0:
            await add_referral_earnings(ref_id, ref_bonus)
            try:
                await callback.bot.send_message(
                    ref_id,
                    f"🎉 <b>Referal bonusi!</b>\n\n"
                    f"Do'stingiz hisobini to'ldirdi va sizga <b>+{format_uzs(ref_bonus)}</b> bonus berildi!",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # 4. Foydalanuvchiga xabar yuborish
    try:
        await callback.bot.send_message(
            user_id,
            f"✅ <b>Hisobingiz muvaffaqiyatli to'ldirildi!</b>\n\n"
            f"💰 Balansingizga <b>+{format_uzs(amount)}</b> qo'shildi.\n"
            f"Marhamat, buyurtma berishingiz mumkin!",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n✅ <b>ADMIN TOMONIDAN TASDIQLANDI</b>",
        parse_mode="HTML"
    )
    await callback.answer("To'lov tasdiqlandi!")

@router.callback_query(F.data.startswith("adm_pay_no_"))
async def callback_admin_reject_payment(callback: CallbackQuery):
    payment_id = int(callback.data.split("_")[3])
    payment = await get_payment(payment_id)

    if not payment:
        await callback.answer("To'lov topilmadi.", show_alert=True)
        return

    if payment["status"] != "PENDING":
        await callback.answer("Bu to'lov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    await update_payment_status(payment_id, "REJECTED")

    try:
        await callback.bot.send_message(
            payment["user_id"],
            "❌ <b>To'lov chekingiz rad etildi.</b>\n\n"
            "Iltimos, haqiqiy chekni yuborganingizga ishonch hosil qiling yoki qo'llab-quvvatlash xizmati bilan bog'laning.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n❌ <b>ADMIN TOMONIDAN RAD ETILDI</b>",
        parse_mode="HTML"
    )
    await callback.answer("To'lov rad etildi!")
