from sqlalchemy.orm import Session

from app.models import AuditLog


def audit(db: Session, user_id: int | None, action: str, entity_type: str | None = None,
          entity_id: int | str | None = None, **meta) -> None:
    """Append an audit record (never include secrets or full financial details in meta)."""
    db.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type,
                    entity_id=None if entity_id is None else str(entity_id), meta=meta))
