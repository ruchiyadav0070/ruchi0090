from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Inventory Management System"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:12345678@localhost:5432/inventory_db"
    FRONTEND_ORIGIN: str = "http://localhost:3000"

settings = Settings()