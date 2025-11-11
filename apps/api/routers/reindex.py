from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from time import perf_counter
from services.indexer.run import run_reindex

router = APIRouter()

class ReindexRequest(BaseModel):
    full: bool = True
    since: str | None = None
    source: str = Field(default="seed", pattern="^(seed|db)$")
    batch_size: int = 1000

class ReindexResponse(BaseModel):
    upserts: int
    skipped: int
    duration_ms: int

@router.post("/reindex", response_model=ReindexResponse)
def reindex(req: ReindexRequest):
    t0 = perf_counter()
    try:
        upserts, skipped = run_reindex(
            full=req.full, since=req.since, source=req.source, batch_size=req.batch_size
        )
        return ReindexResponse(
            upserts=upserts, skipped=skipped, duration_ms=int((perf_counter() - t0) * 1000)
        )
    except Exception as e:
        # error JSON amigable para que `jq` no se rompa
        raise HTTPException(
            status_code=500,
            detail={"code": "REINDEX_ERROR", "message": str(e)}
        )
