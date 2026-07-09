import logging
from decimal import Decimal, InvalidOperation
from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from src.config import settings
from src.database.engine import AsyncSessionLocal
from src.database.models import Product

router = Router()
log = logging.getLogger(__name__)


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.admin_ids


@router.message(Command("add_product"))
async def cmd_add_product(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return

    text = message.text or ""
    parts = [part.strip() for part in text.split("|", maxsplit=4)]
    if len(parts) not in {4, 5}:
        await message.answer("Формат: /add_product | Название | Цена | Контент | Описание")
        return

    _, name, price_raw, content, *description_parts = parts
    description = description_parts[0] if description_parts else "Описание товара"

    try:
        price = Decimal(price_raw)
    except InvalidOperation:
        await message.answer("Цена должна быть числом.")
        return

    if not name or not content or price <= 0:
        await message.answer("Название и контент обязательны, цена должна быть больше нуля.")
        return

    async with AsyncSessionLocal() as session:
        session.add(
            Product(
                name=name[:255],
                description=description or "Описание товара",
                price_usdt=price,
                content=content,
            )
        )
        await session.commit()

    log.info("admin=%s added product=%s", message.from_user.id, name)
    await message.answer(f"Товар «{escape(name)}» добавлен.")


@router.message(Command("products"))
async def cmd_products(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product).order_by(Product.id))
        products = list(result.scalars())

    if not products:
        await message.answer("Товаров нет.")
        return

    lines = [
        f"{'✅' if p.is_active else '❌'} <b>{p.id}</b>. {escape(p.name[:60])} — {p.price_usdt:g} USDT"
        for p in products
    ]
    await message.answer("Товары:\n" + "\n".join(lines))


@router.message(Command("del_product"))
async def cmd_del_product(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Формат: /del_product &lt;id&gt;")
        return

    try:
        product_id = int(parts[1].strip())
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    async with AsyncSessionLocal() as session:
        product = await session.get(Product, product_id)
        if product is None:
            await message.answer("Товар не найден.")
            return
        if not product.is_active:
            await message.answer("Товар уже скрыт.")
            return
        product.is_active = False
        await session.commit()

    log.info("admin=%s hid product_id=%s", message.from_user.id, product_id)
    await message.answer(f"Товар «{escape(product.name)}» скрыт из каталога.")


@router.message(Command("restore_product"))
async def cmd_restore_product(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Формат: /restore_product &lt;id&gt;")
        return

    try:
        product_id = int(parts[1].strip())
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    async with AsyncSessionLocal() as session:
        product = await session.get(Product, product_id)
        if product is None:
            await message.answer("Товар не найден.")
            return
        if product.is_active:
            await message.answer("Товар уже активен.")
            return
        product.is_active = True
        await session.commit()

    log.info("admin=%s restored product_id=%s", message.from_user.id, product_id)
    await message.answer(f"Товар «{escape(product.name)}» снова доступен.")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return

    await message.answer(
        "Команды администратора:\n"
        "<code>/add_product | Название | Цена | Контент | Описание</code>\n"
        "<code>/products</code> — список товаров\n"
        "<code>/del_product &lt;id&gt;</code> — скрыть товар\n"
        "<code>/restore_product &lt;id&gt;</code> — вернуть товар"
    )
