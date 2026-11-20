from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = ROOT / "apps" / "web" / "dist"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    keitaro_url: str
    keitaro_api_key: str
    keitaro_domain: str
    keitaro_group: str
    keitaro_source: str
    default_geo: str
    database_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
