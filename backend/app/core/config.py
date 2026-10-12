import os
import shutil
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure GitPython finds git on Windows
os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")
default_git = Path(r"C:\Users\vsb\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe")
if default_git.exists() and not os.environ.get("GIT_PYTHON_GIT_EXECUTABLE"):
    os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = str(default_git)
    # Also prepend to system PATH
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

    # Base Paths
    BACKEND_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BACKEND_DIR / "data"
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    VECTOR_STORE_DIR: Path = DATA_DIR / "vector_store"

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BACKEND_DIR}/data/docpilot.db"

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
        self.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
