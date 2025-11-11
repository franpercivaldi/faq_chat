# services/indexer/run.py
from __future__ import annotations
from typing import Tuple, Optional, List, Dict, Any
from packages.config.settings import settings
from services.indexer.pipelines.faq_ingest import reindex_from_seed, _to_text
from packages.adapters.db.sql import DbFaqReader
from packages.adapters.llm.gemini import embed_documents
from packages.adapters.vector.qdrant_store import QdrantStore

def run_reindex(full: bool = True, since: Optional[str] = None, source: str = "seed", batch_size: int = 1000) -> Tuple[int, int]:
    if source == "seed":
        return reindex_from_seed(settings.SEED_FAQS_PATH)

    if source != "db":
        raise ValueError("source debe ser 'seed' o 'db'")

    reader = DbFaqReader()
    store = QdrantStore()
    total_upserts = 0
    ensured = False

    for items in reader.iter_faqs(since_iso=(None if full else since), batch_size=batch_size):
        texts = [_to_text(it) for it in items]
        vecs = embed_documents(texts)
        if not ensured:
            store.ensure_collection(len(vecs[0]))
            ensured = True
        total_upserts += store.upsert(items, vecs)

    # skipped = 0 (MVP; cuando agreguemos hash, lo actualizamos)
    return total_upserts, 0
