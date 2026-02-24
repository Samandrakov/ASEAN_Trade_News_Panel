from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./asean_news.db"
    anthropic_api_key: str = ""
    scrape_interval_hours: int = 6
    scrape_delay_seconds: float = 2.0
    llm_model_tagging: str = "claude-sonnet-4-20250514"
    llm_model_summarize: str = "claude-opus-4-20250514"
    llm_batch_size: int = 5
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"]

    # Auth
    admin_username: str = "admin"
    admin_password_hash: str = ""
    jwt_secret: str = "CHANGE-ME-generate-a-random-secret-key"
    jwt_expire_minutes: int = 1440

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
