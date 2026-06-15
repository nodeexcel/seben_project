from pathlib import Path

from pydantic_settings import BaseSettings

_ROOT_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = _ROOT_DIR / ".env"


class Settings(BaseSettings):
    database_url: str = "postgresql://seben:seben123@localhost:5432/seben_crm"
    secret_key: str = "dev-secret-key"
    debug: bool = True
    cors_origins: str = "http://localhost:5173"
    openai_api_key: str = ""
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"


settings = Settings()
