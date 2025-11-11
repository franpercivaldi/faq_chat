from fastapi import APIRouter
from qdrant_client import QdrantClient
from packages.config.settings import settings

router = APIRouter()

@router.get("")
def health():
    qdrant_status = "down"
    try:
        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            timeout=2.0,
        )
        # ping ligero: listar colecciones (no crea nada)
        _ = client.get_collections()
        qdrant_status = "ok"
    except Exception as e:
        qdrant_status = f"down:{type(e).__name__}"

    env_ok = bool(settings.ROLES_CONFIG_PATH)
    gemini_key_present = bool(settings.GEMINI_API_KEY)

    return {
        "ok": qdrant_status == "ok" and env_ok,
        "qdrant": qdrant_status,
        "env": {"roles_config": env_ok, "gemini_key_present": gemini_key_present},
        "version": "0.1.0",
    }
