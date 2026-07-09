from aiogram.filters.callback_data import CallbackData


class ProductCallback(CallbackData, prefix="prod"):
    product_id: int


class BuyCallback(CallbackData, prefix="buy"):
    product_id: int


class CheckInvoiceCallback(CallbackData, prefix="check_inv"):
    invoice_id: int
