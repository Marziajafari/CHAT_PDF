"""Application settings, read from environment variables / backend/.env."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # the backend/ folder


class Settings(BaseSettings):
    app_name: str = "StudyMate AI"
    debug: bool = False
    frontend_origin: str = "http://localhost:5173"

    # Local AI (Ollama)
    ollama_url: str = "http://localhost:11434"
    chat_model: str = "llama3.2:1b"
    ollama_timeout: int = 240
    ollama_num_ctx: int = 4096
    ollama_num_predict: int = 512
    ollama_keep_alive: str = "5m"

    # Embeddings
    embedding_backend: str = "sentence-transformers"  # or "hash" (tests only)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Documents
    chunk_size: int = 700
    chunk_overlap: int = 100
    max_upload_mb: int = 20
    embed_batch_size: int = 32

    # Retrieval
    top_k: int = 4
    relevance_threshold: float = 0.25
    history_messages: int = 6
    max_context_chars: int = 3000

    data_dir: Path = BASE_DIR / "data"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'studymate.sqlite').as_posix()}"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.upload_dir, self.chroma_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
