from aiocryptopay import AioCryptoPay, Networks

from src.config import settings


crypto_client = AioCryptoPay(
    token=settings.cryptopay_token.get_secret_value(),
    network=Networks.MAIN_NET,
)
