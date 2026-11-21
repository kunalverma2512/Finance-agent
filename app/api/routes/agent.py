from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DB, LLM, CurrentUser
from app.core.rate_limit import chat_rate_limit
from app.schemas.agent import ChatIn, ChatOut, MessageOut, RunOut
from app.services.agent import AgentService

router = APIRouter()


@router.post("/agent/chat", response_model=ChatOut)
def chat(data: ChatIn, user: CurrentUser, db: DB, llm: LLM):
    chat_rate_limit(user.id)
    return AgentService(db, user, llm).chat(data.message)


@router.get("/agent/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, user: CurrentUser, db: DB):
    r = AgentService(db, user, None).get_run(run_id)
    return RunOut(run_id=r.id, intent=r.intent, status=r.status, started_at=r.started_at,
                  finished_at=r.finished_at, steps=r.steps, tools_used=r.tools_used, error=r.error,
                  result=r.result)


@router.get("/agent/messages", response_model=list[MessageOut])
def history(user: CurrentUser, db: DB, limit: Annotated[int, Query(ge=1, le=100)] = 30):
    return [MessageOut(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
            for m in AgentService(db, user, None).history(limit)]
