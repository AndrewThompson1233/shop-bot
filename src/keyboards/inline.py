from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.database.models import P
from src.keyboards.callbacks import BuyCB, CheckInvCB, ProdCB


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        ]
    )


def get_cat_kb(prods: list[P]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{p.name} — {p.price_usdt:g} USDT",
                callback_data=ProdCB(product_id=p.id).pack(),
            )
        ]
        for p in prods
    ]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_prod_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Купить", callback_data=BuyCB(product_id=pid).pack())],
            [InlineKeyboardButton(text="🔙 В каталог", callback_data="catalog")],
        ]
    )


def get_pay_kb(url: str, inv_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Оплатить", url=url)],
            [
                InlineKeyboardButton(
                    text="🔄 Проверить оплату",
                    callback_data=CheckInvCB(invoice_id=inv_id).pack(),
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="catalog")],
        ]
    )
