from __future__ import annotations
from typing import List, Tuple, Dict, Any
from packages.adapters.llm.gemini import embed_queries
from packages.adapters.vector.qdrant_store import QdrantStore

def retrieve(query: str, allowed_segments: List[int], top_k: int = 5):
    vec = embed_queries([query])[0]
    store = QdrantStore()
    res = store.search(vec, allowed_segments, top_k)
    out = []
    for sp in res:
        pl = sp.payload or {}
        out.append((
            int(pl.get("faq_id")),
            int(pl.get("segment_id")),
            float(sp.score),
            pl.get("link"),
            pl.get("answer"),
            pl.get("question"),
        ))
    return out

def build_context(results: List[tuple], max_docs: int) -> List[Dict[str, Any]]:
    ctx = []
    for (fid, sid, score, link, ans, q) in results[:max_docs]:
        ctx.append({"faq_id": fid, "segment_id": sid, "score": score, "link": link, "answer": ans or "", "question": q or ""})
    return ctx
