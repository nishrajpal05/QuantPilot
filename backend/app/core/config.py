from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus


class Settings(BaseSettings):
    # Database
    database_url: str = ""
    user: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[str] = None
    dbname: Optional[str] = None

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # Groq
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    groq_api_key_fallback: str = ""

    # Redis
    redis_url: str = ""

    # App
    environment: str = "development"
    allowed_origins: str = "http://localhost:5173"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @model_validator(mode="after")
    def build_database_url(self):
        if all([self.user, self.password, self.host, self.port, self.dbname]):
            user = quote_plus(self.user)
            password = quote_plus(self.password)
            self.database_url = (
                f"postgresql://{user}:{password}@{self.host}:{self.port}/{self.dbname}"
            )
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        return self

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
