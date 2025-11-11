# packages/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    COLLECTION_NAME: str = "faq_es_v1"

    # BD (Postgres RDS)
    DATABASE_URL: str | None = None
    DB_HOST: str | None = None
    DB_PORT: int = 5432
    DB_NAME: str | None = None
    DB_USERNAME: str | None = None
    DB_PASSWORD: str | None = None
    DB_SSLMODE: str = "require"
    DB_TABLE: str = "public.helper_questions"

    # 🔹 Mapeo de columnas (personalizable por .env)
    DB_COL_ID: str = "id"
    DB_COL_SEGMENT_ID: str = "segment_id"
    DB_COL_QUESTION: str = "question"
    DB_COL_RESPONSE: str = "response"
    DB_COL_LINK: str | None = "link"
    DB_COL_CREATED_AT: str | None = "created_at"
    DB_COL_UPDATED_AT: str | None = "updated_at"
    DB_COL_IS_ACTIVE: str | None = None        # ej. "is_active"
    DB_ACTIVE_TRUE: str = "TRUE"               # si usan flag activo int/bool, cambia a "1" o similar

    # LLM
    GEMINI_API_KEY: str | None = None
    EMBEDDINGS_MODEL: str = "gemini-embedding-001"
    GENERATION_MODEL: str = "gemini-2.5-flash"
    EMBEDDINGS_FAKE: bool = False

    # RAG
    RAG_TOP_K: int = 5
    RAG_MIN_SCORE: float = 0.20
    RAG_HIGH_THRESHOLD: float = 0.75
    RAG_GAP: float = 0.12
    RAG_MAX_DOCS: int = 5
    RAG_MAX_CHARS: int = 4000
    ALWAYS_RAG: bool = True
    EXACT_REWRITE_WITH_LLM: bool = False

    # Roles/idioma
    ROLES_CONFIG_PATH: str = "packages/config/roles.json"
    LANG_DEFAULT: str = "es"
    DEFAULT_ROLE: str = "public"

    # Seed (fallback)
    SEED_FAQS_PATH: str = "packages/config/seed_faqs.json"

    def load_roles(self) -> dict[str, list[int]]:
        p = Path(self.ROLES_CONFIG_PATH)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def pg_dsn(self) -> str | None:
        url = (self.DATABASE_URL or "").strip()
        # ignorar placeholders accidentales
        if url and "user:pass@host:5432/dbname" not in url and "user:pass@host" not in url:
            return url
        if self.DB_HOST and self.DB_NAME:
            auth = ""
            if self.DB_USERNAME or self.DB_PASSWORD:
                user = self.DB_USERNAME or ""
                pwd = self.DB_PASSWORD or ""
                auth = f"{user}:{pwd}@"
            return f"postgresql://{auth}{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?sslmode={self.DB_SSLMODE}"
        return None

settings = Settings()
