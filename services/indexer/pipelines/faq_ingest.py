from __future__ import annotations
from typing import List, Dict, Any, Tuple
from pathlib import Path
import json

from packages.adapters.llm.gemini import embed_documents
from packages.adapters.vector.qdrant_store import QdrantStore

def _load_seed(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    for d in data:
        d["faq_id"] = int(d["faq_id"])
        d["segment_id"] = int(d["segment_id"])
    return data

def _to_text(it: Dict[str, Any]) -> str:
    return f"{it['question'].strip()}\n{it['response'].strip()}"

def reindex_from_seed(seed_path: str) -> Tuple[int, int]:
    items = _load_seed(seed_path)
    if not items:
        return (0, 0)

    texts = [_to_text(it) for it in items]
    vecs = embed_documents(texts)
    vector_size = len(vecs[0])

    store = QdrantStore()
    store.ensure_collection(vector_size)
    upserts = store.upsert(items, vecs)
    skipped = 0
    return (upserts, skipped)
