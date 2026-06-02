from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., description="Database connection URL")
    GEMINI_API_KEY: str = Field(..., description="Gemini API Key")
    QDRANT_HOST: str = Field(..., description="Qdrant host address")
    QDRANT_PORT: int = Field(..., description="Qdrant port")
    QDRANT_COLLECTION_NAME: str = Field(..., description="Qdrant collection name")
    EMBEDDING_MODEL: str = Field(
        ..., description="HuggingFace model ID for sentence-transformers"
    )
    LLM_MODEL: str = Field(..., description="Gemini model ID")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore
