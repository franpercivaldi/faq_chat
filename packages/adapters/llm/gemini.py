from __future__ import annotations
from typing import List, Dict
from packages.config.settings import settings
from pathlib import Path
from typing import Optional

# Embeddings (como ya lo dejaste)
def _fake_embed(texts: List[str], dim: int = 256) -> List[List[float]]:
    import hashlib, numpy as np
    out: List[List[float]] = []
    for t in texts:
        seed = int.from_bytes(hashlib.sha256(t.encode("utf-8")).digest()[:8], "big")
        rng = np.random.default_rng(seed)
        v = rng.standard_normal(dim).astype("float32")
        v /= (np.linalg.norm(v) + 1e-9)
        out.append(v.tolist())
    return out

def _gemini_embed(texts: List[str], task_type: str) -> List[List[float]]:
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    vectors: List[List[float]] = []
    for t in texts:
        # The google.generativeai client expects model names in the form
        # 'models/...' or 'tunedModels/...'. Normalize legacy names by
        # prefixing with 'models/' when missing to avoid "Invalid model name" errors.
        model_name = _normalize_model_name(settings.EMBEDDINGS_MODEL)
        res = genai.embed_content(model=model_name, content=t, task_type=task_type)
        vectors.append(res["embedding"])
    return vectors

def embed_documents(texts: List[str]) -> List[List[float]]:
    if settings.EMBEDDINGS_FAKE or not settings.GEMINI_API_KEY:
        return _fake_embed(texts)
    return _gemini_embed(texts, task_type="retrieval_document")

def embed_queries(texts: List[str]) -> List[List[float]]:
    if settings.EMBEDDINGS_FAKE or not settings.GEMINI_API_KEY:
        return _fake_embed(texts)
    return _gemini_embed(texts, task_type="retrieval_query")


def _normalize_model_name(name: Optional[str]) -> str:
    """Ensure model name starts with 'models/' or 'tunedModels/'.

    If name is falsy, return it as-is (caller must handle missing API key case).
    """
    if not name:
        return ""
    name = name.strip()
    if name.startswith("models/") or name.startswith("tunedModels/"):
        return name
    # Prefix with 'models/' to match the google.generativeai expected format.
    return f"models/{name}"

# -------- NUEVO: generación RAG --------
def generate_answer(question: str, context_docs: List[Dict[str, str]], lang: str = "es") -> str:
    """
    context_docs: lista de dicts con {"question": str, "answer": str, "link": str|None}
    """
    # Fallback simple cuando no hay clave o en entorno offline
    if not settings.GEMINI_API_KEY:
        # Devolvemos la mejor respuesta disponible del contexto
        for d in context_docs:
            if d.get("answer"):
                return d["answer"]
        return "No encuentro información en las FAQ para responder."

    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    # Armamos el contexto plano (recortado)
    docs_txt = []
    total = 0
    for d in context_docs[: settings.RAG_MAX_DOCS]:
        chunk = f"Q: {d.get('question','')}\nA: {d.get('answer','')}\n"
        if d.get("link"):
            chunk += f"LINK: {d['link']}\n"
        docs_txt.append(chunk)
        total += len(chunk)
        if total >= settings.RAG_MAX_CHARS:
            break

    context_block = "\n---\n".join(docs_txt)
    system = Path("packages/prompts/system_es.txt").read_text(encoding="utf-8")

    gen_model_name = _normalize_model_name(settings.GENERATION_MODEL)
    model = genai.GenerativeModel(gen_model_name, system_instruction=system)
    # Pedimos respuesta concisa y fiel al contexto
    prompt = f"Usuario: {question}\n\nCONTEXTO:\n{context_block}\n\nInstrucciones: respondé SOLO con lo del contexto. Idioma: {lang}."
    res = model.generate_content(prompt)
    # Manejo básico de seguridad/empty
    txt = getattr(res, "text", None) or (res.candidates[0].content.parts[0].text if getattr(res, "candidates", None) else "")
    txt = txt.strip() or ""

    # Detectar respuestas tipo "no encuentro" y fallback al mejor contexto
    low = txt.lower()
    negative_markers = [
        "no encuentro", "no encuentro información", "no encuentro información en",
        "no hay información", "no está en las faq", "no está en las preguntas frecuentes",
        "no puedo encontrar", "nothing found", "no results", "not found",
    ]

    if not txt:
        # vacío -> fallback
        fallback = _first_answer_in_context(context_docs)
        return fallback

    for m in negative_markers:
        if m in low:
            fallback = _first_answer_in_context(context_docs)
            return fallback

    return txt


def _first_answer_in_context(context_docs: List[Dict[str, str]]) -> str:
    """Return the first non-empty answer from context_docs, or a default message."""
    for d in context_docs:
        a = d.get("answer")
        if a and a.strip():
            return a.strip()
    return "No encuentro información en las FAQ para responder."
