from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatOut(BaseModel):
    run_id: str
    intent: str | None
    status: str
    response: str
    tools_used: list[str]


class RunOut(BaseModel):
    run_id: str
    intent: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    steps: int
    tools_used: list[Any]
    error: str | None
    result: dict | None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
