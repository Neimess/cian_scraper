from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./project.db"
    LOGGER_MODE: str = "console"
    TELEGRAM_API_KEY: str
    TELEGRAM_ADMIN_ID: str
    PROXIES: list[str] = []
    
    model_config = ConfigDict(extra="ignore", env_file=".env")


settings = Settings()