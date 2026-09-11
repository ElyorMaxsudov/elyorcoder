import aiosqlite
from typing import Optional, Dict, Any, List
from config import DATABASE_PATH

async def init_db():
    """Ma'lumotlar bazasini va jadvallarni ishga tushirish."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                download_count INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                is_telegram_premium INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cached_songs (
                song_id TEXT PRIMARY KEY,
                title TEXT,
                artist TEXT,
                duration INTEGER,
                file_id TEXT,
                downloads_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def get_or_create_user(user_id: int, username: Optional[str], full_name: str, is_tg_premium: bool = False) -> Dict[str, Any]:
    """Foydalanuvchini bazadan olish yoki yangi qo'shish."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO users (user_id, username, full_name, download_count, is_vip, is_telegram_premium)
            VALUES (?, ?, ?, 0, 0, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                is_telegram_premium = CASE WHEN excluded.is_telegram_premium = 1 THEN 1 ELSE users.is_telegram_premium END
            """,
            (user_id, username, full_name, 1 if is_tg_premium else 0)
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row)

async def increment_user_download(user_id: int) -> int:
    """Foydalanuvchi yuklab olgan musiqalar sonini 1 taga oshirish."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET download_count = download_count + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
        cursor = await db.execute("SELECT download_count FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def can_user_download(user_id: int, free_limit: int, auto_tg_premium: bool = True) -> tuple[bool, int, int, bool]:
    """
    Foydalanuvchi musiqa yuklab olishi mumkinligini tekshiradi.
    Qaytaradi: (mumkinmi, hozirgi_soni, limit, vip_holati)
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT download_count, is_vip, is_telegram_premium FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        
        if not row:
            return True, 0, free_limit, False
            
        download_count = row["download_count"]
        is_vip = bool(row["is_vip"])
        is_tg_prem = bool(row["is_telegram_premium"])
        
        # Agar VIP bo'lsa yoki Telegram Premiumga ruxsat yoqilgan bo'lsa
        if is_vip or (auto_tg_premium and is_tg_prem):
            return True, download_count, free_limit, True
            
        # Agar limitdan kam yuklagan bo'lsa
        if download_count < free_limit:
            return True, download_count, free_limit, False
            
        # Limit tugagan
        return False, download_count, free_limit, False

async def set_user_vip(user_id: int, status: bool = True) -> bool:
    """Foydalanuvchiga VIP / Premium berish yoki bekor qilish."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET is_vip = ? WHERE user_id = ?",
            (1 if status else 0, user_id)
        )
        await db.commit()
        return True

async def get_cached_song(song_id: str) -> Optional[Dict[str, Any]]:
    """Keshdagi musiqani Telegram file_id si bilan olish."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM cached_songs WHERE song_id = ?", (song_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE cached_songs SET downloads_count = downloads_count + 1 WHERE song_id = ?",
                (song_id,)
            )
            await db.commit()
            return dict(row)
        return None

async def save_cached_song(song_id: str, title: str, artist: str, duration: int, file_id: str):
    """Musiqa Telegram file_id sini keshga saqlash (qayta yuklamaslik uchun)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO cached_songs (song_id, title, artist, duration, file_id, downloads_count)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(song_id) DO UPDATE SET file_id = excluded.file_id
            """,
            (song_id, title, artist, duration, file_id)
        )
        await db.commit()

async def get_stats() -> Dict[str, Any]:
    """Umumiy bot statistikasini olish."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor_users = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor_users.fetchone())[0]
        
        cursor_vip = await db.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1 OR is_telegram_premium = 1")
        total_vip = (await cursor_vip.fetchone())[0]
        
        cursor_downloads = await db.execute("SELECT SUM(download_count) FROM users")
        total_downloads = (await cursor_downloads.fetchone())[0] or 0
        
        cursor_cached = await db.execute("SELECT COUNT(*) FROM cached_songs")
        total_cached = (await cursor_cached.fetchone())[0]
        
        return {
            "total_users": total_users,
            "total_vip": total_vip,
            "total_downloads": total_downloads,
            "total_cached": total_cached
        }

async def get_all_user_ids() -> List[int]:
    """Barcha foydalanuvchilar ID ro'yxatini olish (Broadcast uchun)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
