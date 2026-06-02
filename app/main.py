from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.observability.logging import setup_logging
from app.db.repository import init_db
from app.rag.indexer import index_knowledge_base
import structlog

setup_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("database_initialized")

    await index_knowledge_base()
    logger.info("knowledge_base_indexed")

    logger.info("application_started", service="bookleaf_bot")
    yield
    logger.info("application_shutdown")

app = FastAPI(title="BookLeaf AI Query Bot", lifespan=lifespan)
app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
