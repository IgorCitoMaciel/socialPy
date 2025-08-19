from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Configurações básicas
    PROJECT_NAME: str = "FastAPI Project"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Configurações do banco de dados
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    
    # Configurações de segurança
    SECRET_KEY: str = "your-secret-key-here"  # Em produção, use uma chave secreta segura
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings() 