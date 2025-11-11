from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    role: Optional[str] = Field(default=None, description="Rol del usuario (p.ej. 'Secretaria')")
    lang: Optional[str] = Field(default=None, description="Idioma del usuario (default: settings.LANG_DEFAULT)")
    trace_id: Optional[str] = None

class ChatSource(BaseModel):
    faq_id: int
    segment_id: int
    score: float
    link: Optional[str] = None

class ChatResponse(BaseModel):
    mode: Literal["DEBUG", "EXACT", "RAG"]
    answer: str
    sources: List[ChatSource] = []
    meta: dict = {}
