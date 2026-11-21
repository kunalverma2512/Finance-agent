"""Typed tool registry. The agent can ONLY call tools registered here (no raw SQL, no shell)."""
import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import User

log = logging.getLogger(__name__)


class ToolError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code, self.message, self.retryable = code, message, retryable


@dataclass
class ToolContext:
    db: Session
    user: User
    today: date


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable[[ToolContext, Any], dict]
    mutating: bool = False


REGISTRY: dict[str, ToolSpec] = {}


def tool(name: str, args_model: type[BaseModel], description: str, mutating: bool = False):
    def deco(fn: Callable[[ToolContext, Any], dict]):
        REGISTRY[name] = ToolSpec(name, description, args_model, fn, mutating)
        return fn
    return deco


def jsonable(value: Any) -> Any:
    """Decimal -> exact string, date -> ISO. Money never becomes a float."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def run_tool(name: str, raw_args: dict, ctx: ToolContext) -> dict:
    spec = REGISTRY.get(name)
    if spec is None:
        raise ToolError("UNKNOWN_TOOL", f"Tool '{name}' is not available")
    try:
        args = spec.args_model.model_validate(raw_args or {})
        return jsonable(spec.fn(ctx, args))
    except ValidationError as exc:
        raise ToolError("INVALID_ARGUMENTS", "; ".join(e["msg"] for e in exc.errors())[:300]) from exc
    except AppError as exc:
        ctx.db.rollback()
        raise ToolError(exc.code, exc.message) from exc
    except OperationalError as exc:
        ctx.db.rollback()
        log.warning("tool_transient_db_error", extra={"tool": name})
        raise ToolError("DB_UNAVAILABLE", "Temporary database problem", retryable=True) from exc
    except ToolError:
        raise
    except Exception as exc:  # never leak internals to the model or the user
        ctx.db.rollback()
        log.exception("tool_failed", extra={"tool": name})
        raise ToolError("INTERNAL_ERROR", "The tool failed unexpectedly") from exc
