from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict

class IntentResult(BaseModel):
    intent: Literal[
        "BOOK_STATUS", "ROYALTY", "AUTHOR_COPY", "ADD_ON", "SALES", "GENERAL", "UNKNOWN"
    ]
    extracted_entity: Optional[Dict[str, str]] = None
    reasoning: str
    confidence: float

class RetrievedContext(BaseModel):
    source_id: str
    content: str
    source_type: Literal["db", "kb"]
    score: float = 1.0

class AgentState(BaseModel):
    correlation_id: str
    query: str
    channel: str
    identifier: str
    author_id: Optional[str] = None
    identity_confidence: Optional[float] = None
    intent_result: Optional[IntentResult] = None
    retrieved_contexts: List[RetrievedContext] = Field(default_factory=list)
    final_response: Optional[str] = None
    overall_confidence: Optional[float] = None
    is_escalated: bool = False
    query_log_id: Optional[str] = None
    latency_ms: Optional[int] = None
    tokens_used: int = 0
    start_time: Optional[float] = None
