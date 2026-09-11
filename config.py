import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Asosiy yo'llar
BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Bot token (@BotFather dan olinadi)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Bot adminining Telegram ID si (@userinfobot orqali bilish mumkin)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Bepul yuklab olish limiti (Odatiy: 1000 ta qo'shiq)
FREE_DOWNLOAD_LIMIT = int(os.getenv("FREE_DOWNLOAD_LIMIT", "1000"))

# Telegram Premium foydalanuvchilariga avtomatik cheksiz ruxsat berish
AUTO_TELEGRAM_PREMIUM_VIP = os.getenv("AUTO_TELEGRAM_PREMIUM_VIP", "True").lower() in ("true", "1", "yes")

# Majburiy a'zolik kanali (agar bo'lsa: "@kanal_nomi", bo'lmasa bo'sh qoldiring)
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")

# Ma'lumotlar bazasi fayli
DATABASE_PATH = BASE_DIR / "bot_database.sqlite3"
