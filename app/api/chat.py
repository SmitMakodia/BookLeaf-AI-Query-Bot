from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repository import get_db, Repository
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse
from app.agent.graph import AgentWorkflow
from app.config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, session: AsyncSession = Depends(get_db)):
    try:
        repo = Repository(session)
        workflow = AgentWorkflow(repo)
        final_state = await workflow.invoke(
            query=request.query,
            channel=request.channel,
            identifier=request.identifier,
        )

        sources = [ctx.source_id for ctx in final_state.retrieved_contexts]
        
        log_id = None
        try:
            log_id = await repo.log_query({
                "correlation_id": final_state.correlation_id,
                "author_id": final_state.author_id,
                "channel": final_state.channel,
                "raw_query": final_state.query,
                "intent": final_state.intent_result.intent if final_state.intent_result else "UNKNOWN",
                "identity_confidence": final_state.identity_confidence,
                "retrieval_sources": sources,
                "response_text": final_state.final_response,
                "confidence": final_state.overall_confidence,
                "escalated": final_state.is_escalated,
                "latency_ms": final_state.latency_ms,
                "llm_model": settings.LLM_MODEL if final_state.intent_result else None,
                "tokens_used": final_state.tokens_used,
            })
        except Exception as e:
            logger.error("query_log_failed", error=str(e))

        if final_state.is_escalated and log_id:
            try:
                await repo.create_escalation({
                    "query_log_id": log_id,
                    "author_id": final_state.author_id,
                    "bot_response": final_state.final_response,
                    "confidence": final_state.overall_confidence,
                })
                logger.info("escalation_created", correlation_id=final_state.correlation_id,
                            confidence=final_state.overall_confidence)
            except Exception as e:
                logger.error("escalation_write_failed", error=str(e))

        return ChatResponse(
            correlation_id=final_state.correlation_id,
            response=final_state.final_response or "No response generated.",
            confidence=final_state.overall_confidence or 0.0,
            escalated=final_state.is_escalated,
            sources=sources,
            intent=final_state.intent_result.intent if final_state.intent_result else "UNKNOWN",
            author_id=final_state.author_id,
            identity_confidence=final_state.identity_confidence,
        )

    except Exception as e:
        logger.error("chat_endpoint_error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={
                "response": "Something went wrong. A BookLeaf team member will follow up.",
                "escalated": True,
                "confidence": 0.0,
                "sources": [],
                "correlation_id": "error",
                "intent": "UNKNOWN",
            }
        )
