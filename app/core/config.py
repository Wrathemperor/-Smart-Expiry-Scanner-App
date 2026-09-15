from pydantic_settings import BaseSettings,SettingsConfigDict
from pathlib import Path

#Project root
BASE_DIR=Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    APP_NAME: str="ShelfSense Gateway"
    APP_VERSION: str="1.0.0"
    API_PREFIX: str="/api/v1"
    HOST: str="0.0.0.0"
    PORT: int=8000
    DATABASE_URL: str=f"sqlite:///{BASE_DIR/'database'/'shelfsense.db'}"
    IMAGE_DIRECTORY: Path=BASE_DIR/"app"/"images"
    DEBUG: bool=True
    S3_BUCKET_NAME: str="shelfsense-images-app"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
   
settings=Settings()