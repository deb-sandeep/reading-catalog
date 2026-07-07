from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class AppConfig(BaseModel):
    db_url: str
    log_level: str = "INFO"


class OpenLibrarySourceConfig(BaseModel):
    base_url: str
    user_agent: str
    timeout_seconds: float = 10
    max_retries: int = 3
    request_delay_seconds: float = 0.5


class HardcoverSourceConfig(BaseModel):
    enabled: bool = False
    base_url: str


class GoogleBooksSourceConfig(BaseModel):
    enabled: bool = False
    base_url: str


class SourcesConfig(BaseModel):
    openlibrary: OpenLibrarySourceConfig
    hardcover: HardcoverSourceConfig
    googlebooks: GoogleBooksSourceConfig


class OpenLibraryDiscoveryConfig(BaseModel):
    subjects: list[str]
    limit_per_subject: int = 20


class DiscoveryConfig(BaseModel):
    openlibrary: OpenLibraryDiscoveryConfig


class FiltersConfig(BaseModel):
    min_rating: float = 4.0
    reader_threshold_mode: str = "percentile"
    reader_percentile: int = 75
    reader_absolute_floor: int = 10000


class Config(BaseModel):
    app: AppConfig
    sources: SourcesConfig
    discovery: DiscoveryConfig
    filters: FiltersConfig


def load_config(path: str | Path = "config.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    return Config.model_validate(raw)
