from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select
from src.database.engine import AsyncSessionLocal
from src.database.models import Product
from src.config import settings

router = Router()

@router.message(Command("add_product"))
async def cmd_add_product(message: Message) -> None:
    if message.from_user.id not in settings.admin_ids:
        return

    try:
        _, name, price, content = message.text.split("|")
        price = float(price.strip())
        name = name.strip()
        content = content.strip()
    except ValueError:
        await message.answer("Формат: /add_product | Название | 5.5 | Секретный контент/ссылка")
        return

    async with AsyncSessionLocal() as session:
        new_product = Product(
            name=name,
            description="Описание товара",
            price_usdt=price,
            content=content
        )
        session.add(new_product)
        await session.commit()
    
    await message.answer(f"Товар '{name}' успешно добавлен в базу.")