import asyncio
from aiogram import Bot, Dispatcher
from src.config import settings
from src.database.engine import init_db
from src.handlers import user, admin

async def main() -> None:
    await init_db()
    
    bot = Bot(token=settings.bot_token.get_secret_value())
    dp = Dispatcher()
    
    dp.include_router(admin.router)
    dp.include_router(user.router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())