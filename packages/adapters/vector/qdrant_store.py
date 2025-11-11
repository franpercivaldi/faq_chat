from __future__ import annotations
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchAny
from packages.config.settings import settings

class QdrantStore:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        self.collection = settings.COLLECTION_NAME

    def ensure_collection(self, vector_size: int):
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def upsert(self, items: List[Dict[str, Any]], vectors: List[List[float]]) -> int:
        points = []
        for it, vec in zip(items, vectors):
            payload = {
                "faq_id": it["faq_id"],
                "segment_id": it["segment_id"],
                "question": it["question"],
                "answer": it["response"],
                "link": it.get("link"),
                "created_at": it.get("created_at"),
            }
            points.append(PointStruct(id=int(it["faq_id"]), vector=vec, payload=payload))

        self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    def search(self, query_vector: List[float], allowed_segments: List[int], top_k: int):
        flt = Filter(must=[FieldCondition(key="segment_id", match=MatchAny(any=allowed_segments))])
        return self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
            query_filter=flt,  # older clients used 'filter', 1.9.x accepts 'query_filter'
        )
