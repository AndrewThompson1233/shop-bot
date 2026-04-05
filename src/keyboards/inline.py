from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.keyboards.callbacks import ProductCallback, BuyCallback, CheckInvoiceCallback
from src.database.models import Product

def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
        ]
    )

def get_catalog_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{product.name} — {product.price_usdt} USDT",
                callback_data=ProductCallback(product_id=product.id).pack()
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💳 Купить", callback_data=BuyCallback(product_id=product_id).pack())],[InlineKeyboardButton(text="🔙 В каталог", callback_data="catalog")]
        ]
    )

def get_payment_keyboard(url: str, invoice_id: int, product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Оплатить", url=url)],[InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=CheckInvoiceCallback(invoice_id=invoice_id, product_id=product_id).pack())],[InlineKeyboardButton(text="❌ Отмена", callback_data="catalog")]
        ]
    )