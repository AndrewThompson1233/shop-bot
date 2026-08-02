import logging as log
from decimal import Decimal, InvalidOperation
from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from src.config import settings
from src.database.engine import ASL
from src.database.models import P

router = Router()
lg = log.getLogger(__name__)


def is_admin(uid: int | None) -> bool:
    return uid is not None and uid in settings.admin_ids


@router.message(Command("add_product"))
async def cmd_add_product(msg: Message) -> None:
    if not is_admin(msg.from_user.id if msg.from_user else None):
        return

    txt = msg.text or ""
    parts = [p.strip() for p in txt.split("|", maxsplit=4)]
    if len(parts) not in {4, 5}:
        await msg.answer("Формат: /add_product | Название | Цена | Контент | Описание")
        return

    _, name, price_raw, content, *desc_parts = parts
    desc = desc_parts[0] if desc_parts else "Описание товара"

    try:
        price = Decimal(price_raw)
    except InvalidOperation:
        await msg.answer("Цена должна быть числом.")
        return

    if not name or not content or price <= 0:
        await msg.answer("Название и контент обязательны, цена должна быть больше нуля.")
        return

    async with ASL() as s:
        s.add(
            P(
                name=name[:255],
                description=desc or "Описание товара",
                price_usdt=price,
                content=content,
            )
        )
        await s.commit()

    lg.info("admin=%s added product=%s", msg.from_user.id, name)
    await msg.answer(f"Товар «{escape(name)}» добавлен.")


@router.message(Command("products"))
async def cmd_products(msg: Message) -> None:
    if not is_admin(msg.from_user.id if msg.from_user else None):
        return

    async with ASL() as s:
        res = await s.execute(select(P).order_by(P.id))
        prods = list(res.scalars())

    if not prods:
        await msg.answer("Товаров нет.")
        return

    lines = [
        f"{'✅' if p.is_active else '❌'} <b>{p.id}</b>. {escape(p.name[:60])} — {p.price_usdt:g} USDT"
        for p in prods
    ]
    await msg.answer("Товары:\n" + "\n".join(lines))


@router.message(Command("del_product"))
async def cmd_del_product(msg: Message) -> None:
    if not is_admin(msg.from_user.id if msg.from_user else None):
        return

    parts = (msg.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Формат: /del_product &lt;id&gt;")
        return

    try:
        pid = int(parts[1].strip())
    except ValueError:
        await msg.answer("ID должен быть числом.")
        return

    async with ASL() as s:
        prod = await s.get(P, pid)
        if prod is None:
            await msg.answer("Товар не найден.")
            return
        if not prod.is_active:
            await msg.answer("Товар уже скрыт.")
            return
        prod.is_active = False
        await s.commit()

    lg.info("admin=%s hid product_id=%s", msg.from_user.id, pid)
    await msg.answer(f"Товар «{escape(prod.name)}» скрыт из каталога.")


@router.message(Command("restore_product"))
async def cmd_restore_product(msg: Message) -> None:
    if not is_admin(msg.from_user.id if msg.from_user else None):
        return

    parts = (msg.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Формат: /restore_product &lt;id&gt;")
        return

    try:
        pid = int(parts[1].strip())
    except ValueError:
        await msg.answer("ID должен быть числом.")
        return

    async with ASL() as s:
        prod = await s.get(P, pid)
        if prod is None:
            await msg.answer("Товар не найден.")
            return
        if prod.is_active:
            await msg.answer("Товар уже активен.")
            return
        prod.is_active = True
        await s.commit()

    lg.info("admin=%s restored product_id=%s", msg.from_user.id, pid)
    await msg.answer(f"Товар «{escape(prod.name)}» снова доступен.")


@router.message(Command("help"))
async def cmd_help(msg: Message) -> None:
    if not is_admin(msg.from_user.id if msg.from_user else None):
        return

    await msg.answer(
        "Команды администратора:\n"
        "<code>/add_product | Название | Цена | Контент | Описание</code>\n"
        "<code>/products</code> — список товаров\n"
        "<code>/del_product &lt;id&gt;</code> — скрыть товар\n"
        "<code>/restore_product &lt;id&gt;</code> — вернуть товар"
    )
