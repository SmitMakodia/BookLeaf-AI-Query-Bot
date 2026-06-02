import asyncio
import os
from sentence_transformers import SentenceTransformer
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from app.config import settings

qdrant_client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

def get_embedding(text: str) -> list[float]:
    return embedding_model.encode(text).tolist()

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks

async def index_knowledge_base():
    file_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "knowledge_base", "bookleaf_kb.md"
    )
    if not os.path.exists(file_path):
        import structlog
        structlog.get_logger().warning("kb_file_not_found", path=file_path)
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = chunk_text(content, chunk_size=400, overlap=80)

    collections = await qdrant_client.get_collections()
    existing = [c.name for c in collections.collections]
    if settings.QDRANT_COLLECTION_NAME in existing:
        info = await qdrant_client.get_collection(settings.QDRANT_COLLECTION_NAME)
        if info.points_count and info.points_count > 0:
            return

    if settings.QDRANT_COLLECTION_NAME not in existing:
        test_embedding = get_embedding("test")
        await qdrant_client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(size=len(test_embedding), distance=Distance.COSINE),
        )

    points = []
    for idx, chunk in enumerate(chunks):
        points.append(PointStruct(
            id=idx,
            vector=get_embedding(chunk),
            payload={"content": chunk, "chunk_id": f"kb:chunk_{idx}"},
        ))

    if points:
        await qdrant_client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME, points=points
        )

if __name__ == "__main__":
    asyncio.run(index_knowledge_base())
