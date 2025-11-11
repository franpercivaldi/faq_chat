from __future__ import annotations
from typing import List, Dict
from packages.config.settings import settings
from pathlib import Path

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
        res = genai.embed_content(model=settings.EMBEDDINGS_MODEL, content=t, task_type=task_type)
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

    model = genai.GenerativeModel(settings.GENERATION_MODEL, system_instruction=system)
    # Pedimos respuesta concisa y fiel al contexto
    prompt = f"Usuario: {question}\n\nCONTEXTO:\n{context_block}\n\nInstrucciones: respondé SOLO con lo del contexto. Idioma: {lang}."
    res = model.generate_content(prompt)
    # Manejo básico de seguridad/empty
    txt = getattr(res, "text", None) or (res.candidates[0].content.parts[0].text if getattr(res, "candidates", None) else "")
    return txt.strip() or "No encuentro información en las FAQ para responder."
