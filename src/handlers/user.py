import logging as log
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from src.database.engine import ASL
from src.database.models import I, P, U
from src.keyboards.callbacks import BuyCB, CheckInvCB, ProdCB
from src.keyboards.inline import get_cat_kb, get_main_menu, get_pay_kb, get_prod_kb
from src.services.cryptopay import CC

router = Router()
lg = log.getLogger(__name__)


async def edit_msg(cb: CallbackQuery, txt: str, **kw: object) -> None:
    if not cb.message:
        return
    try:
        await cb.message.edit_text(txt, **kw)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise


@router.message(CommandStart())
async def cmd_start(msg: Message) -> None:
    if not msg.from_user:
        return

    async with ASL() as s:
        res = await s.execute(select(U).where(U.telegram_id == msg.from_user.id))
        u = res.scalar_one_or_none()
        if u is None:
            s.add(U(telegram_id=msg.from_user.id, username=msg.from_user.username))
        elif u.username != msg.from_user.username:
            u.username = msg.from_user.username
        await s.commit()

    await msg.answer("Добро пожаловать в магазин цифровых товаров.", reply_markup=get_main_menu())


@router.callback_query(F.data == "main_menu")
async def proc_main_menu(cb: CallbackQuery) -> None:
    await cb.answer()
    await edit_msg(cb, "Главное меню:", reply_markup=get_main_menu())


@router.callback_query(F.data == "profile")
async def proc_profile(cb: CallbackQuery) -> None:
    async with ASL() as s:
        u_res = await s.execute(select(U).where(U.telegram_id == cb.from_user.id))
        u = u_res.scalar_one_or_none()
        purch = 0
        if u:
            purch = await s.scalar(
                select(func.count(I.id)).where(I.user_id == u.id, I.status == "paid")
            ) or 0

    await cb.answer()
    txt = f"👤 <b>Профиль</b>\n\nID: <code>{cb.from_user.id}</code>\nУспешных покупок: {purch}"
    await edit_msg(cb, txt, reply_markup=get_main_menu())


@router.callback_query(F.data == "catalog")
async def proc_catalog(cb: CallbackQuery) -> None:
    async with ASL() as s:
        res = await s.execute(select(P).where(P.is_active.is_(True)).order_by(P.id))
        prods = list(res.scalars())

    await cb.answer()
    if not prods:
        await edit_msg(cb, "Каталог пуст.", reply_markup=get_main_menu())
        return
    await edit_msg(cb, "Выберите товар:", reply_markup=get_cat_kb(prods))


@router.callback_query(ProdCB.filter())
async def proc_product(cb: CallbackQuery, cd: ProdCB) -> None:
    async with ASL() as s:
        prod = await s.scalar(
            select(P).where(P.id == cd.product_id, P.is_active.is_(True))
        )

    if prod is None:
        await cb.answer("Товар не найден.", show_alert=True)
        return

    await cb.answer()
    txt = (
        f"📦 <b>{escape(prod.name)}</b>\n\n{escape(prod.description)}\n\n"
        f"Цена: {prod.price_usdt:g} USDT"
    )
    await edit_msg(cb, txt, reply_markup=get_prod_kb(prod.id))


@router.callback_query(BuyCB.filter())
async def proc_buy(cb: CallbackQuery, cd: BuyCB) -> None:
    async with ASL() as s:
        u = await s.scalar(select(U).where(U.telegram_id == cb.from_user.id))
        prod = await s.scalar(
            select(P).where(P.id == cd.product_id, P.is_active.is_(True))
        )

        if u is None or prod is None:
            await cb.answer("Пользователь или товар не найден.", show_alert=True)
            return

        try:
            inv = await CC.create_invoice(
                asset="USDT",
                amount=prod.price_usdt,
                description=f"Оплата товара: {prod.name}"[:1024],
            )
        except Exception:
            lg.exception("create_invoice failed user=%s product=%s", cb.from_user.id, prod.id)
            await cb.answer("Не удалось создать счет. Попробуйте позже.", show_alert=True)
            return

        s.add(
            I(
                crypto_invoice_id=inv.invoice_id,
                user_id=u.id,
                product_id=prod.id,
            )
        )
        await s.commit()

        price = prod.price_usdt
        url = inv.bot_invoice_url
        inv_id = inv.invoice_id

    await cb.answer()
    await edit_msg(
        cb,
        f"Оплатите счет на сумму {price:g} USDT.",
        reply_markup=get_pay_kb(url, inv_id),
    )


@router.callback_query(CheckInvCB.filter())
async def proc_check_inv(cb: CallbackQuery, cd: CheckInvCB) -> None:
    async with ASL() as s:
        db_inv = await s.scalar(
            select(I)
            .join(U, U.id == I.user_id)
            .where(
                I.crypto_invoice_id == cd.invoice_id,
                U.telegram_id == cb.from_user.id,
            )
        )
        if db_inv is None:
            await cb.answer("Счет не найден.", show_alert=True)
            return
        if db_inv.status == "paid":
            await cb.answer("Этот счет уже был обработан.", show_alert=True)
            return

        try:
            invoices = await CC.get_invoices(invoice_ids=cd.invoice_id)
        except Exception:
            lg.exception("get_invoices failed invoice=%s", cd.invoice_id)
            await cb.answer("Не удалось проверить оплату. Попробуйте позже.", show_alert=True)
            return

        if not invoices or invoices[0].status != "paid":
            await cb.answer("Оплата еще не поступила. Попробуйте позже.", show_alert=True)
            return

        prod = await s.get(P, db_inv.product_id)
        if prod is None:
            await cb.answer("Товар больше недоступен. Обратитесь к администратору.", show_alert=True)
            return

        db_inv.status = "paid"
        await s.commit()

        content = prod.content

    await cb.answer()
    await edit_msg(
        cb,
        f"✅ <b>Оплата успешна!</b>\n\nВаш товар:\n<code>{escape(content)}</code>",
        reply_markup=get_main_menu(),
    )
