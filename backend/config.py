from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    RABBITMQ_URL: str
    RABBITMQ_INFERENCE_QUEUE: str = "inference_logs"
    RABBITMQ_PREFETCH_COUNT: int = Field(default=10, ge=1, le=1000)
    CONTEXT_WINDOW_MESSAGES: int = Field(ge=1, le=50)
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
