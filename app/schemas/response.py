from pydantic import BaseModel
from typing import Optional, List


class ChatResponse(BaseModel):
    correlation_id: str
    response: str
    confidence: float
    escalated: bool
    sources: List[str]
    intent: Optional[str] = None
    author_id: Optional[str] = None
    identity_confidence: Optional[float] = None
