import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    telegram_token: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    usd_rub: float
    amplitude_api_key: str
    user_id_salt: str


def load_config() -> Config:
    return Config(
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        deepseek_api_key=os.environ["DEEPSEEK_API_KEY"],
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        usd_rub=float(os.getenv("USD_RUB", "80")),
        amplitude_api_key=os.getenv("AMPLITUDE_API_KEY", ""),
        user_id_salt=os.getenv("USER_ID_SALT", "change-me"),
    )
