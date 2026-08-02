from aiogram.filters.callback_data import CallbackData


class ProdCB(CallbackData, prefix="prod"):
    product_id: int


class BuyCB(CallbackData, prefix="buy"):
    product_id: int


class CheckInvCB(CallbackData, prefix="check_inv"):
    invoice_id: int
