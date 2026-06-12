from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://seben:seben_dev_password@localhost:5432/seben_crm"
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
        env_file = ".env"
        extra = "ignore"


settings = Settings()
