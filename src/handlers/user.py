import logging
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from src.database.engine import AsyncSessionLocal
from src.database.models import Invoice, Product, User
from src.keyboards.callbacks import BuyCallback, CheckInvoiceCallback, ProductCallback
from src.keyboards.inline import get_catalog_keyboard, get_main_menu, get_payment_keyboard, get_product_keyboard
from src.services.cryptopay import crypto_client

router = Router()
log = logging.getLogger(__name__)


async def edit_message(callback: CallbackQuery, text: str, **kwargs: object) -> None:
    if not callback.message:
        return
    try:
        await callback.message.edit_text(text, **kwargs)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error).lower():
            raise


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not message.from_user:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            session.add(User(telegram_id=message.from_user.id, username=message.from_user.username))
        elif user.username != message.from_user.username:
            user.username = message.from_user.username
        await session.commit()

    await message.answer("Добро пожаловать в магазин цифровых товаров.", reply_markup=get_main_menu())


@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_message(callback, "Главное меню:", reply_markup=get_main_menu())


@router.callback_query(F.data == "profile")
async def process_profile(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = user_result.scalar_one_or_none()
        purchases = 0
        if user:
            purchases = await session.scalar(
                select(func.count(Invoice.id)).where(Invoice.user_id == user.id, Invoice.status == "paid")
            ) or 0

    await callback.answer()
    text = f"👤 <b>Профиль</b>\n\nID: <code>{callback.from_user.id}</code>\nУспешных покупок: {purchases}"
    await edit_message(callback, text, reply_markup=get_main_menu())


@router.callback_query(F.data == "catalog")
async def process_catalog(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product).where(Product.is_active.is_(True)).order_by(Product.id))
        products = list(result.scalars())

    await callback.answer()
    if not products:
        await edit_message(callback, "Каталог пуст.", reply_markup=get_main_menu())
        return
    await edit_message(callback, "Выберите товар:", reply_markup=get_catalog_keyboard(products))


@router.callback_query(ProductCallback.filter())
async def process_product(callback: CallbackQuery, callback_data: ProductCallback) -> None:
    async with AsyncSessionLocal() as session:
        product = await session.scalar(
            select(Product).where(Product.id == callback_data.product_id, Product.is_active.is_(True))
        )

    if product is None:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    await callback.answer()
    text = (
        f"📦 <b>{escape(product.name)}</b>\n\n{escape(product.description)}\n\n"
        f"Цена: {product.price_usdt:g} USDT"
    )
    await edit_message(callback, text, reply_markup=get_product_keyboard(product.id))


@router.callback_query(BuyCallback.filter())
async def process_buy(callback: CallbackQuery, callback_data: BuyCallback) -> None:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        product = await session.scalar(
            select(Product).where(Product.id == callback_data.product_id, Product.is_active.is_(True))
        )

        if user is None or product is None:
            await callback.answer("Пользователь или товар не найден.", show_alert=True)
            return

        try:
            invoice = await crypto_client.create_invoice(
                asset="USDT",
                amount=product.price_usdt,
                description=f"Оплата товара: {product.name}"[:1024],
            )
        except Exception:
            log.exception("create_invoice failed user=%s product=%s", callback.from_user.id, product.id)
            await callback.answer("Не удалось создать счет. Попробуйте позже.", show_alert=True)
            return

        session.add(
            Invoice(
                crypto_invoice_id=invoice.invoice_id,
                user_id=user.id,
                product_id=product.id,
            )
        )
        await session.commit()

        price = product.price_usdt
        url = invoice.bot_invoice_url
        inv_id = invoice.invoice_id

    await callback.answer()
    await edit_message(
        callback,
        f"Оплатите счет на сумму {price:g} USDT.",
        reply_markup=get_payment_keyboard(url, inv_id),
    )


@router.callback_query(CheckInvoiceCallback.filter())
async def process_check_invoice(callback: CallbackQuery, callback_data: CheckInvoiceCallback) -> None:
    async with AsyncSessionLocal() as session:
        db_invoice = await session.scalar(
            select(Invoice)
            .join(User, User.id == Invoice.user_id)
            .where(
                Invoice.crypto_invoice_id == callback_data.invoice_id,
                User.telegram_id == callback.from_user.id,
            )
        )
        if db_invoice is None:
            await callback.answer("Счет не найден.", show_alert=True)
            return
        if db_invoice.status == "paid":
            await callback.answer("Этот счет уже был обработан.", show_alert=True)
            return

        try:
            invoices = await crypto_client.get_invoices(invoice_ids=callback_data.invoice_id)
        except Exception:
            log.exception("get_invoices failed invoice=%s", callback_data.invoice_id)
            await callback.answer("Не удалось проверить оплату. Попробуйте позже.", show_alert=True)
            return

        if not invoices or invoices[0].status != "paid":
            await callback.answer("Оплата еще не поступила. Попробуйте позже.", show_alert=True)
            return

        product = await session.get(Product, db_invoice.product_id)
        if product is None:
            await callback.answer("Товар больше недоступен. Обратитесь к администратору.", show_alert=True)
            return

        db_invoice.status = "paid"
        await session.commit()

        content = product.content

    await callback.answer()
    await edit_message(
        callback,
        f"✅ <b>Оплата успешна!</b>\n\nВаш товар:\n<code>{escape(content)}</code>",
        reply_markup=get_main_menu(),
    )
