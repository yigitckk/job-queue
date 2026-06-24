from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI App"
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG_MODE: bool = False

    class Config:
        env_file=".env"

settings = Settings()


