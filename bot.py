import asyncio
import logging
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import init_db
from handlers import start, search, link_downloader, admin

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def set_commands(bot: Bot):
    """Bot menyusi uchun buyruqlar ro'yxati."""
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="profile", description="Mening profilim va limitlarim"),
        BotCommand(command="help", description="Yordam va qo'llanma"),
    ]
    await bot.set_my_commands(commands)

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "\n[XATOLIK] BOT_TOKEN sozlanmagan!\n"
            "Iltimos, .env faylini oching va Telegram @BotFather dan olgan tokenni yozing.\n"
            "Masalan: BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ\n"
        )
        return

    # Ma'lumotlar bazasini ishga tushirish
    logger.info("Ma'lumotlar bazasi tekshirilmoqda...")
    await init_db()

    # Bot va Dispatcher yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Routerlarni ulash (tartibi muhim)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(link_downloader.router)
    dp.include_router(search.router)

    # Buyruqlarni menyuga o'rnatish
    await set_commands(bot)

    # Bot ma'lumotlarini olish
    bot_info = await bot.get_me()
    logger.info(f"Bot muvaffaqiyatli ishga tushdi: @{bot_info.username}")
    print("\n" + "=" * 50)
    print(f"  🎵 TELEGRAM MUSIC BOT ISHGA TUSHDI: @{bot_info.username}")
    print("=" * 50 + "\n")

    # Pollingni boshlash
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
