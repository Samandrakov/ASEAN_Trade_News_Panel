from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./asean_news.db"
    anthropic_api_key: str = ""
    scrape_interval_hours: int = 6
    scrape_delay_seconds: float = 2.0
    llm_model_tagging: str = "claude-sonnet-4-20250514"
    llm_model_summarize: str = "claude-opus-4-20250514"
    llm_batch_size: int = 5
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
