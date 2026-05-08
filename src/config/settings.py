from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    data_dir: Path = Path("./dataset")
    indices_dir: Path = Path("./indices")
    phh_dir: Path = Path("./dataset/phh_hands")
    dps_dir: Path = Path("./dataset/dps")
    profiles_path: Path = Path("./dataset/villain_profiles/profiles.parquet")
    log_level: str = "INFO"
    api_v2_prefix: str = "/api/v2"
    cache_ttl_seconds: int = Field(default=300, ge=0)


settings = Settings()
