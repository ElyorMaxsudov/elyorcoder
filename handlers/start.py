from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from database import get_or_create_user, get_referral_stats, get_setting
from keyboards.reply import get_main_menu
from utils.formatters import format_uzs
from config import ADMIN_IDS, REFERRAL_PERCENT

router = Router()

async def is_user_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    admin_id_setting = await get_setting("admin_id", "")
    if admin_id_setting and str(user_id) == admin_id_setting.strip():
        return True
    return False

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    referrer_id = None
    args = command.args
    if args:
        if args.startswith("ref_") and args[4:].isdigit():
            referrer_id = int(args[4:])
        elif args.isdigit():
            referrer_id = int(args)

    user = await get_or_create_user(
        user_id=user_id,
        username=username,
        full_name=full_name,
        referrer_id=referrer_id
    )

    admin_status = await is_user_admin(user_id)

    welcome_text = (
        f"👋 <b>Assalomu alaykum, {full_name}!</b>\n\n"
        f"🚀 <b>Eng sifatli va arzon SMM xizmatlari botiga xush kelibsiz!</b>\n\n"
        f"Bizning bot orqali siz:\n"
        f"• <b>Telegram</b> (Kafolatli obunachilar, ko'rishlar, reaksiyalar)\n"
        f"• <b>Instagram</b> (Obunachilar, layklar, reels ko'rishlar)\n"
        f"• <b>TikTok</b> (Obunachilar, layklar, ko'rishlar)\n"
        f"• <b>YouTube</b> (Obunachi, ko'rishlar, layklar)\n"
        f"• <b>Telegram Stars</b> (Xarid qilish va balans to'ldirish)\n\n"
        f"💡 Kerakli bo'limni quyidagi menyudan tanlang:"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(is_admin=admin_status),
        parse_mode="HTML"
    )

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    admin_status = await is_user_admin(message.from_user.id)
    await message.answer(
        "❌ Amaliyot bekor qilindi.",
        reply_markup=get_main_menu(is_admin=admin_status)
    )

@router.message(F.text == "👥 Referal tizimi")
async def referral_handler(message: Message):
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    count, earnings = await get_referral_stats(user_id)

    text = (
        f"👥 <b>Do'stlarni taklif qilish va daromad olish!</b>\n\n"
        f"Do'stlaringizni taklif qiling va ular hisobini to'ldirganda <b>{REFERRAL_PERCENT}%</b> "
        f"miqdorida naqd bonusga ega bo'ling!\n\n"
        f"📊 <b>Sizning statistikangiz:</b>\n"
        f"• Taklif qilingan do'stlar: <b>{count} ta</b>\n"
        f"• Ishlangan jami daromad: <b>{format_uzs(earnings)}</b>\n\n"
        f"🔗 <b>Sizning referal havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"<i>Ushbu havolani do'stlaringizga yoki kanallaringizga ulashing!</i>"
    )
    await message.answer(text, parse_mode="HTML")
