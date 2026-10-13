import os
import shutil
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure GitPython finds git on Windows
os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")
default_git = Path(r"C:\Users\vsb\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe")
if default_git.exists() and not os.environ.get("GIT_PYTHON_GIT_EXECUTABLE"):
    os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = str(default_git)
    os.environ["PATH"] = str(default_git.parent) + os.pathsep + os.environ.get("PATH", "")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "DocPilot AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Base Paths
    BACKEND_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BACKEND_DIR / "data"
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    PROJECTS_DIR: Path = BACKEND_DIR / "data" / "projects"
    VECTOR_STORE_DIR: Path = BACKEND_DIR / "data" / "vector_store"

    # Database Configuration (PostgreSQL supported, SQLite local fallback)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BACKEND_DIR}/data/docpilot.db"

    # File & ZIP Upload limits
    MAX_UPLOAD_SIZE_MB: int = 100
    IGNORED_DIRECTORIES: List[str] = [
        "node_modules",
        ".git",
        "__pycache__",
        "dist",
        "build",
        ".venv",
        "venv",
        "env",
        ".next",
        ".cache",
        ".idea",
        ".vscode",
        "coverage",
        ".pytest_cache",
        "target",
    ]

    # AI Provider Settings
    LLM_PROVIDER: str = "openai"  # openai, gemini, anthropic, ollama, custom
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "https://api.openai.com/v1"

    # Embedding Provider Settings
    EMBEDDING_PROVIDER: str = "openai"  # openai, local
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Vector Store
    VECTOR_STORE_TYPE: str = "local"

    # Integrations
    GITHUB_TOKEN: Optional[str] = None

    def ensure_directories(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
