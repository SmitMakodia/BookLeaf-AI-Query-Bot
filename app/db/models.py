import uuid
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Column,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass


def generate_uuid():
    return str(uuid.uuid4())


class Author(Base):
    __tablename__ = "authors"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), index=True)
    instagram = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Book(Base):
    __tablename__ = "books"

    id = Column(String, primary_key=True, default=generate_uuid)
    author_id = Column(String, ForeignKey("authors.id", ondelete="CASCADE"), index=True)
    book_title = Column(String(500), nullable=False)
    isbn = Column(String(20), unique=True)
    final_submission_date = Column(Date)
    book_live_date = Column(Date)
    royalty_status = Column(String(50))
    add_on_services = Column(JSON, default=list)
    author_copy_status = Column(String(50), default="NOT_DISPATCHED")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PlatformIdentifier(Base):
    __tablename__ = "platform_identifiers"

    id = Column(String, primary_key=True, default=generate_uuid)
    author_id = Column(String, ForeignKey("authors.id", ondelete="CASCADE"))
    platform = Column(String(50), nullable=False)
    identifier = Column(String(255), nullable=False)
    verified = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_platform_identifiers_lookup", "platform", "identifier"),
    )


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    correlation_id = Column(String, nullable=False)
    author_id = Column(String, ForeignKey("authors.id"), index=True)
    channel = Column(String(50))
    raw_query = Column(String, nullable=False)
    intent = Column(String(50))
    identity_confidence = Column(Float)
    retrieval_sources = Column(JSON)
    response_text = Column(String)
    confidence = Column(Float)
    escalated = Column(Boolean, default=False)
    latency_ms = Column(Integer)
    llm_model = Column(String(100))
    tokens_used = Column(Integer)
    created_at = Column(DateTime, server_default=func.now(), index=True)


class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(String, primary_key=True, default=generate_uuid)
    query_log_id = Column(String, ForeignKey("query_logs.id"))
    author_id = Column(String, ForeignKey("authors.id"))
    bot_response = Column(String)
    confidence = Column(Float)
    status = Column(String(20), default="OPEN", index=True)
    human_response = Column(String)
    resolved_by = Column(String(255))
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
