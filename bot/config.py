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
    db_path: str

    @property
    def llm_mode(self) -> str:
        """mock — без ключа DeepSeek (ответ-заглушка), real — настоящая модель."""
        forced = os.getenv("LLM_MODE", "").strip().lower()
        if forced in ("mock", "real"):
            return forced
        return "real" if self.deepseek_api_key else "mock"


def load_config(require_telegram: bool = True) -> Config:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if require_telegram and not token:
        raise SystemExit("Не задан TELEGRAM_BOT_TOKEN (см. .env.example)")
    return Config(
        telegram_token=token,
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        usd_rub=float(os.getenv("USD_RUB", "80")),
        amplitude_api_key=os.getenv("AMPLITUDE_API_KEY", ""),
        user_id_salt=os.getenv("USER_ID_SALT", "change-me"),
        db_path=os.getenv("DB_PATH", "data/bot.sqlite3"),
    )
