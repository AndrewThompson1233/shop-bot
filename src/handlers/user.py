from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from sqlalchemy import select
from src.database.engine import AsyncSessionLocal
from src.database.models import User, Product, Invoice
from src.services.cryptopay import crypto_client
from src.keyboards.inline import (
    get_main_menu,
    get_catalog_keyboard,
    get_product_keyboard,
    get_payment_keyboard
)
from src.keyboards.callbacks import ProductCallback, BuyCallback, CheckInvoiceCallback

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            new_user = User(telegram_id=message.from_user.id, username=message.from_user.username)
            session.add(new_user)
            await session.commit()
    
    await message.answer(
        "Добро пожаловать в магазин цифровых товаров.",
        reply_markup=get_main_menu()
    )

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=get_main_menu()
    )

@router.callback_query(F.data == "profile")
async def process_profile(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Invoice).where(Invoice.user_id == callback.from_user.id, Invoice.status == "paid")
        )
        purchases = result.scalars().all()
    
    text = f"👤 <b>Профиль</b>\n\nID: <code>{callback.from_user.id}</code>\nУспешных покупок: {len(purchases)}"
    await callback.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="HTML")

@router.callback_query(F.data == "catalog")
async def process_catalog(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product).where(Product.is_active == True))
        products = result.scalars().all()
    
    if not products:
        await callback.message.edit_text("Каталог пуст.", reply_markup=get_main_menu())
        return

    await callback.message.edit_text("Выберите товар:", reply_markup=get_catalog_keyboard(products))

@router.callback_query(ProductCallback.filter())
async def process_product(callback: CallbackQuery, callback_data: ProductCallback) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product).where(Product.id == callback_data.product_id))
        product = result.scalar_one_or_none()
    
    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    text = f"📦 <b>{product.name}</b>\n\n{product.description}\n\nЦена: {product.price_usdt} USDT"
    await callback.message.edit_text(text, reply_markup=get_product_keyboard(product.id), parse_mode="HTML")

@router.callback_query(BuyCallback.filter())
async def process_buy(callback: CallbackQuery, callback_data: BuyCallback) -> None:
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = user_result.scalar_one()

        product_result = await session.execute(select(Product).where(Product.id == callback_data.product_id))
        product = product_result.scalar_one()

        invoice = await crypto_client.create_invoice(
            asset="USDT",
            amount=product.price_usdt,
            description=f"Оплата товара: {product.name}"
        )

        new_invoice = Invoice(
            crypto_invoice_id=invoice.invoice_id,
            user_id=user.id,
            product_id=product.id
        )
        session.add(new_invoice)
        await session.commit()

    await callback.message.edit_text(
        f"Оплатите счет на сумму {product.price_usdt} USDT.",
        reply_markup=get_payment_keyboard(invoice.bot_invoice_url, invoice.invoice_id, product.id)
    )

@router.callback_query(CheckInvoiceCallback.filter())
async def process_check_invoice(callback: CallbackQuery, callback_data: CheckInvoiceCallback) -> None:
    invoices = await crypto_client.get_invoices(invoice_ids=callback_data.invoice_id)
    if not invoices:
        await callback.answer("Счет не найден.", show_alert=True)
        return

    crypto_invoice = invoices[0]

    if crypto_invoice.status == "paid":
        async with AsyncSessionLocal() as session:
            db_inv_result = await session.execute(
                select(Invoice).where(Invoice.crypto_invoice_id == callback_data.invoice_id)
            )
            db_inv = db_inv_result.scalar_one()
            
            if db_inv.status == "paid":
                await callback.answer("Этот счет уже был обработан.", show_alert=True)
                return

            db_inv.status = "paid"
            
            product_result = await session.execute(select(Product).where(Product.id == callback_data.product_id))
            product = product_result.scalar_one()
            
            await session.commit()

        await callback.message.edit_text(
            f"✅ <b>Оплата успешна!</b>\n\nВаш товар:\n<code>{product.content}</code>",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
    else:
        await callback.answer("Оплата еще не поступила. Попробуйте позже.", show_alert=True)