from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.future import select
from typing import Optional, List
from .models import Author, Book, PlatformIdentifier, QueryLog, Escalation, Base
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_author_by_identifier(
        self, platform: str, identifier: str
    ) -> Optional[Author]:
        stmt = select(PlatformIdentifier).where(
            PlatformIdentifier.platform == platform,
            PlatformIdentifier.identifier == identifier,
        )
        result = await self.session.execute(stmt)
        pid = result.scalars().first()
        if pid and pid.author_id:
            return await self.get_author_by_id(str(pid.author_id))
        return None

    async def get_author_by_id(self, author_id: str) -> Optional[Author]:
        stmt = select(Author).where(Author.id == author_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_books_by_author(self, author_id: str) -> List[Book]:
        stmt = select(Book).where(Book.author_id == author_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def log_query(self, log_data: dict) -> str:
        log_entry = QueryLog(**log_data)
        self.session.add(log_entry)
        await self.session.commit()
        return str(log_entry.id)

    async def create_escalation(self, escalation_data: dict) -> str:
        escalation = Escalation(**escalation_data)
        self.session.add(escalation)
        await self.session.commit()
        return str(escalation.id)

    async def get_all_authors(self) -> List[Author]:
        stmt = select(Author)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_platform_identifiers(self) -> List[PlatformIdentifier]:
        stmt = select(PlatformIdentifier)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
