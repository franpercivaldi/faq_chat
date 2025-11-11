from fastapi import APIRouter, HTTPException
from apps.api.schemas.chat import ChatRequest, ChatResponse, ChatSource
from apps.api.schemas.common import ErrorResponse
from packages.core.roles import allowed_segments_for_role
from packages.config.settings import settings
from packages.core.retrieval import retrieve, build_context
from packages.adapters.llm.gemini import generate_answer
from time import perf_counter

router = APIRouter()

@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def chat(req: ChatRequest):
    t0 = perf_counter()
    role = req.role or settings.DEFAULT_ROLE
    allowed_segments = allowed_segments_for_role(role)
    if not allowed_segments:
        raise HTTPException(status_code=400, detail={"code": "ROLE_NOT_MAPPED", "message": f"El rol '{role}' no está mapeado."})

    results = retrieve(req.message, allowed_segments, top_k=settings.RAG_TOP_K)
    if not results:
        raise HTTPException(status_code=404, detail={"code": "NO_RESULTS_FOR_ROLE", "message": "No hay resultados para tu rol o consulta."})

    # Ordenar por score y preparar fuentes
    results_sorted = sorted(results, key=lambda r: r[2], reverse=True)
    best = results_sorted[0]  # (faq_id, segment_id, score, link, answer, question)
    sources = [ChatSource(faq_id=fid, segment_id=sid, score=score, link=link) for (fid, sid, score, link, _ans, _q) in results_sorted]

    lang = req.lang or settings.LANG_DEFAULT

    # ¿Exact o RAG?
    do_rag = settings.ALWAYS_RAG or (best[2] < settings.RAG_HIGH_THRESHOLD)

    if not do_rag and not settings.EXACT_REWRITE_WITH_LLM:
        # ECO EXACTO para máxima fidelidad y menor costo/latencia
        answer = best[4] or ""
        mode = "EXACT"
    else:
        # Generación con Gemini usando los top-N como contexto
        context_docs = build_context(results_sorted, max_docs=settings.RAG_MAX_DOCS)
        answer = generate_answer(req.message, context_docs, lang=lang)
        mode = "RAG" if do_rag else "EXACT"  # EXACT si decidiste reescribir exactos

    return ChatResponse(
        mode=mode,
        answer=answer,
        sources=sources,
        meta={"top_k": settings.RAG_TOP_K, "latency_ms": int((perf_counter() - t0) * 1000), "trace_id": req.trace_id},
    )
