import asyncio
import time
from typing import Any, Dict, Optional
from app.schemas.agent import AgentState, IntentResult
from app.agent.tools import AgentTools
from app.identity.resolver import IdentityResolver
from app.db.repository import Repository
from google import genai
from app.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger()
client = genai.Client(api_key=settings.GEMINI_API_KEY)

class BotError(Exception):
    pass

class LLMUnavailableError(BotError):
    pass

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), reraise=True)
def _call_gemini_sync(
    contents: str, schema: Any = None, system_instruction: Optional[str] = None
) -> Any:
    try:
        config_kwargs: Dict[str, Any] = {"temperature": 0.0}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if schema:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = schema

        response = client.models.generate_content(
            model=settings.LLM_MODEL,
            contents=contents,
            config=genai.types.GenerateContentConfig(**config_kwargs),
        )
        return response
    except Exception as e:
        raise LLMUnavailableError(str(e))

async def call_gemini(
    contents: str, schema: Any = None, system_instruction: Optional[str] = None
) -> Any:
    return await asyncio.to_thread(_call_gemini_sync, contents, schema, system_instruction)

INTENT_SYSTEM_PROMPT = """You are an intent classifier for BookLeaf, an Indian self-publishing company.
Classify the user's query into exactly ONE of these intents:

- BOOK_STATUS: Questions about whether the book is published/live, publishing timeline, submission status
- ROYALTY: Questions about royalty payments, royalty reports, when royalties will be paid, earnings
- AUTHOR_COPY: Questions about physical author copies, delivery status, dispatch, where is my copy
- ADD_ON: Questions about add-on services like Bestseller Package, PR campaign, Awards, ISBN registration
- SALES: Questions about book sales numbers, how many copies sold, sales report
- GENERAL: General questions about BookLeaf policies, processes, timelines not specific to one book
- UNKNOWN: Query cannot be mapped to any of the above

Return a JSON with: intent (string), extracted_entity (dict or null), reasoning (1 sentence), confidence (float 0.0-1.0).
Be strict: only mark GENERAL for policy questions, not for author-specific status queries."""

async def identity_node(state: AgentState, repo: Repository) -> AgentState:
    state.start_time = time.time()
    resolver = IdentityResolver(repo)
    author_id, confidence = await resolver.resolve(state.channel, state.identifier)
    state.author_id = author_id
    state.identity_confidence = confidence
    logger.info("identity_resolved", author_id=author_id, confidence=confidence,
                correlation_id=state.correlation_id)
    return state

async def intent_node(state: AgentState) -> AgentState:
    try:
        response = await call_gemini(
            contents=f"User Query: {state.query}",
            schema=IntentResult,
            system_instruction=INTENT_SYSTEM_PROMPT,
        )
        state.intent_result = IntentResult.model_validate_json(response.text)
        if response.usage_metadata:
            state.tokens_used += response.usage_metadata.total_token_count or 0
    except Exception as e:
        logger.warning("intent_classification_failed", error=str(e),
                       correlation_id=state.correlation_id)
        state.intent_result = IntentResult(
            intent="UNKNOWN",
            extracted_entity=None,
            reasoning=f"Parse Error: {str(e)}",
            confidence=0.0,
        )
    return state

DB_REQUIRED_INTENTS = {"BOOK_STATUS", "ROYALTY", "AUTHOR_COPY", "ADD_ON", "SALES"}

async def retrieval_node(state: AgentState, repo: Repository) -> AgentState:
    tools = AgentTools(repo)
    tasks = []
    task_labels = []

    intent = state.intent_result.intent if state.intent_result else "UNKNOWN"

    if state.author_id and intent in DB_REQUIRED_INTENTS:
        tasks.append(tools.query_db_tool(state.author_id))
        task_labels.append("db")

    tasks.append(tools.query_kb_tool(state.query))
    task_labels.append("kb")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    contexts: list[Any] = []
    for label, result in zip(task_labels, results):
        if isinstance(result, Exception):
            logger.warning("retrieval_failed", source=label, error=str(result),
                           correlation_id=state.correlation_id)
            continue
        contexts.extend(result) # type: ignore

    state.retrieved_contexts = contexts
    logger.info("retrieval_complete", sources_count=len(contexts),
                correlation_id=state.correlation_id)
    return state

GENERATION_SYSTEM_PROMPT = """You are a helpful, professional assistant for BookLeaf, an Indian self-publishing company.
Answer the user's question using ONLY the provided context.

RULES:
1. Cite every factual claim using [source_id] immediately after the statement.
2. If the context contains the answer, answer directly and concisely.
3. If the context does NOT contain the answer, say: "I don't have that information right now."
4. Never fabricate dates, ISBN numbers, royalty amounts, or status values.
5. Be warm and professional"""

async def generate_node(state: AgentState) -> AgentState:
    if not state.retrieved_contexts:
        state.final_response = (
            "I don't have enough information to answer that right now. "
            "A BookLeaf team member will follow up with you shortly."
        )
        return state

    context_str = "\n".join(
        [f"[{c.source_id}] {c.content}" for c in state.retrieved_contexts]
    )
    prompt = (
        f"Context:\n{context_str}\n\n"
        f"User Query: {state.query}\n\n"
        f"Answer using ONLY the context above. Cite every fact with [source_id]."
    )

    try:
        response = await call_gemini(
            contents=prompt,
            system_instruction=GENERATION_SYSTEM_PROMPT,
        )
        state.final_response = response.text or (
            "I was unable to generate a response for that query. "
            "A BookLeaf team member will follow up."
        )
        if response.usage_metadata:
            state.tokens_used += response.usage_metadata.total_token_count or 0
    except LLMUnavailableError as e:
        logger.error("generation_failed", error=str(e), correlation_id=state.correlation_id)
        state.final_response = (
            "I am having trouble right now. A BookLeaf team member will assist you shortly."
        )
    return state

def compute_confidence(state: AgentState) -> float:
    intent_confidence = state.intent_result.confidence if state.intent_result else 0.0
    db_match_found = state.author_id is not None

    sources_cited = sum(
        1 for ctx in state.retrieved_contexts
        if f"[{ctx.source_id}]" in str(state.final_response)
    )

    retrieval_score = (
        max((ctx.score for ctx in state.retrieved_contexts), default=0.0)
        if state.retrieved_contexts else 0.0
    )

    llm_self_score = (
        0.9 if ("[db:" in str(state.final_response) or "[kb:" in str(state.final_response))
        else 0.5
    )

    weights = {"intent": 0.20, "retrieval": 0.25, "db_match": 0.25, "sources": 0.15, "llm_self": 0.15}
    score = (
        weights["intent"] * intent_confidence
        + weights["retrieval"] * retrieval_score
        + weights["db_match"] * (1.0 if db_match_found else 0.3)
        + weights["sources"] * min(sources_cited / 2.0, 1.0)
        + weights["llm_self"] * llm_self_score
    )
    return round(score, 3)

async def confidence_node(state: AgentState) -> AgentState:
    state.overall_confidence = compute_confidence(state)

    if state.start_time:
        state.latency_ms = int((time.time() - state.start_time) * 1000)

    hard_escalate = False
    if state.intent_result and state.intent_result.intent == "UNKNOWN":
        hard_escalate = True
    if (not state.author_id and state.intent_result
            and state.intent_result.intent != "GENERAL"):
        hard_escalate = True

    state.is_escalated = state.overall_confidence < 0.80 or hard_escalate
    logger.info("confidence_scored", score=state.overall_confidence,
                escalated=state.is_escalated, correlation_id=state.correlation_id)
    return state
