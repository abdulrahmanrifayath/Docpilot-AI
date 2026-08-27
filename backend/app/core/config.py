import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "DocPilot AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    # Database
    DATABASE_URL: str = "sqlite:///./docpilot.db"

    # AI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Vector DB
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    VECTOR_COLLECTION_PREFIX: str = "docpilot_"

    # Repository Storage & Upload Limits
    REPO_STORAGE_PATH: str = "./storage/repos"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Ignored directories and files during extraction and file discovery
    IGNORED_DIRECTORIES: List[str] = [
        "node_modules",
        ".git",
        "__pycache__",
        "dist",
        "build",
        ".venv",
        "venv",
        ".next",
        ".nuxt",
        ".idea",
        ".vscode",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "target",
        "vendor",
        "bin",
        "obj",
        "coverage",
        ".turbo",
        ".gradle",
    ]

    IGNORED_FILES: List[str] = [
        ".DS_Store",
        "Thumbs.db",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "Pipfile.lock",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
