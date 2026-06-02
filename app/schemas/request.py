from pydantic import BaseModel, field_validator
from typing import Optional

class ChatRequest(BaseModel):
    query: str
    channel: str
    identifier: str

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty")
        if len(v) > 2000:
            raise ValueError("query too long")
        return v

    @field_validator("channel")
    @classmethod
    def channel_valid(cls, v: str) -> str:
        allowed = {"email", "whatsapp", "instagram", "dashboard", "web"}
        if v.lower() not in allowed:
            raise ValueError(f"channel must be one of {allowed}")
        return v.lower()

class IdentityInput(BaseModel):
    platform: str
    identifier: str
