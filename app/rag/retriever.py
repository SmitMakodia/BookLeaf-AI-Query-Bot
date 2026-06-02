from qdrant_client import AsyncQdrantClient
from app.config import settings
from app.rag.indexer import get_embedding
from app.schemas.agent import RetrievedContext
from typing import List
import structlog
import asyncio

logger = structlog.get_logger()
qdrant_client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)

async def retrieve_from_kb(query: str, top_k: int = 5) -> List[RetrievedContext]:
    try:
        embedding = await asyncio.to_thread(get_embedding, query)
        search_result = await qdrant_client.search(  # type: ignore
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=embedding,
            limit=top_k,
        )
        contexts = []
        for hit in search_result:
            contexts.append(RetrievedContext(
                source_id=hit.payload.get("chunk_id", f"kb:chunk_{hit.id}"),
                content=hit.payload.get("content", ""),
                source_type="kb",
                score=round(float(hit.score), 4),
            ))
        return contexts
    except Exception as e:
        logger.warning("kb_retrieval_failed", error=str(e))
        return []
