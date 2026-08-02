import asyncio as aio
import logging as log

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from src.config import settings
from src.database.engine import close_db, init_db
from src.handlers import admin, user
from src.services.cryptopay import CC

log.basicConfig(
    level=log.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log.getLogger("aiogram.event").setLevel(log.WARNING)

lg = log.getLogger("shop-bot")


async def main() -> None:
    await init_db()

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    dp.include_router(admin.router)
    dp.include_router(user.router)

    lg.info("Bot started")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await CC.close()
        await close_db()
        lg.info("Bot stopped")


if __name__ == "__main__":
    try:
        aio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
