from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.database.models import Product
from src.keyboards.callbacks import BuyCallback, CheckInvoiceCallback, ProductCallback


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        ]
    )


def get_catalog_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{product.name} — {product.price_usdt:g} USDT",
                callback_data=ProductCallback(product_id=product.id).pack(),
            )
        ]
        for product in products
    ]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Купить", callback_data=BuyCallback(product_id=product_id).pack())],
            [InlineKeyboardButton(text="🔙 В каталог", callback_data="catalog")],
        ]
    )


def get_payment_keyboard(url: str, invoice_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Оплатить", url=url)],
            [
                InlineKeyboardButton(
                    text="🔄 Проверить оплату",
                    callback_data=CheckInvoiceCallback(invoice_id=invoice_id).pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="catalog")],
        ]
    )
