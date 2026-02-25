from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Firebase
    firebase_project_id: str
    firebase_private_key_id: str
    firebase_private_key: str
    firebase_client_email: str
    firebase_client_id: str

    # OpenAI
    openai_api_key: str

    # Neon PostgreSQL
    database_url: str

    # SERP
    serp_provider: str = "direct"
    serp_api_key: Optional[str] = None

    # App
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"

    # Token Budget
    monthly_token_cap: int = 500_000

    class Config:
        env_file = ".env"


settings = Settings()
