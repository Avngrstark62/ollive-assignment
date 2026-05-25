from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    CONTEXT_WINDOW_MESSAGES: int = Field(ge=1, le=50)
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
