"""Runs one agent request end-to-end and persists the audit trail (AgentRun + chat messages)."""
import logging
import time
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.agents.graph import build_graph
from app.agents.render import FAILURE_REPLY
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError
from app.integrations.llm import LLMClient
from app.models import AgentRun, User
from app.repositories.finance import CategoryRepo
from app.repositories.planning import AgentRunRepo
from app.tools import ToolContext
from app.tools.registry import jsonable

log = logging.getLogger(__name__)


class AgentService:
    def __init__(self, db: Session, user: User, llm: LLMClient | None, settings: Settings | None = None,
                 today: date | None = None) -> None:
        self.db, self.user, self.llm = db, user, llm
        self.settings = settings or get_settings()
        self.today = today or date.today()
        self.runs = AgentRunRepo(db, user.id)

    def chat(self, message: str) -> dict:
        run_id = str(uuid.uuid4())
        self.runs.add(AgentRun(id=run_id, status="running", tools_used=[]))
        self.runs.add_message("user", message[:self.settings.max_chat_chars * 2], run_id)
        self.db.commit()  # the run exists even if everything below crashes
        started = time.monotonic()
        deps = {"ctx": ToolContext(self.db, self.user, self.today), "llm": self.llm, "settings": self.settings,
                "category_names": [c.name for c in CategoryRepo(self.db, self.user.id).list()]}
        try:
            final = build_graph().invoke({"run_id": run_id, "message": message, "steps": 0},
                                         {"configurable": deps, "recursion_limit": 60})
        except Exception:
            log.exception("agent_graph_crashed", extra={"run_id": run_id})
            self.db.rollback()
            final = {"status": "failed", "error": "graph crashed", "response": FAILURE_REPLY}
        status = final.get("status", "failed")
        tools_used = [{"tool": r["tool"], "ok": r["ok"], "duration_ms": r.get("duration_ms"),
                       **({"error_code": r["error_code"]} if not r["ok"] else {})}
                      for r in final.get("results", []) if not r.get("retrying")]
        run = self.runs.get(run_id)
        run.intent, run.status = final.get("intent"), status
        run.steps, run.tools_used, run.error = final.get("steps", 0), tools_used, final.get("error")
        run.finished_at = datetime.now(timezone.utc)
        run.result = {"response": final["response"], "response_source": final.get("response_source"),
                      "facts": jsonable(final.get("facts", {}))}
        self.runs.add_message("assistant", final["response"], run_id)
        self.db.commit()
        log.info("agent_run_finished", extra={"run_id": run_id, "user_id": self.user.id, "intent": run.intent,
                                              "status": status, "steps": run.steps,
                                              "tools": [t["tool"] for t in tools_used],
                                              "duration_ms": int((time.monotonic() - started) * 1000)})
        return {"run_id": run_id, "intent": run.intent, "status": status, "response": final["response"],
                "tools_used": [t["tool"] for t in tools_used]}

    def get_run(self, run_id: str) -> AgentRun:
        run = self.runs.get(run_id)
        if not run:
            raise NotFoundError("Agent run not found", code="RUN_NOT_FOUND")
        return run

    def history(self, limit: int = 30):
        return self.runs.recent_messages(limit)
