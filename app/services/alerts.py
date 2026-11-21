from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Alert, User
from app.repositories.planning import AlertRepo

ALERT_TYPES = ("UNUSUAL_TRANSACTION", "BUDGET_WARNING", "BUDGET_EXCEEDED", "GOAL_BEHIND", "MONTHLY_INSIGHT")


class AlertService:
    def __init__(self, db: Session, user: User) -> None:
        self.db, self.user = db, user
        self.repo = AlertRepo(db, user.id)

    def page(self, status: str | None, limit: int, offset: int):
        return self.repo.page(status, limit, offset)

    def set_status(self, alert_id: int, status: str) -> Alert:
        alert = self.repo.get(alert_id)
        if not alert:
            raise NotFoundError("Alert not found", code="ALERT_NOT_FOUND")
        alert.status = status
        alert.read_at = datetime.now(timezone.utc) if status != "unread" else None
        self.db.commit()
        return alert

    def mark_all_read(self) -> int:
        n = self.repo.mark_all_read(datetime.now(timezone.utc))
        self.db.commit()
        return n

    def create(self, type_: str, title: str, message: str, severity: str, dedupe_key: str,
               payload: dict | None = None) -> Alert | None:
        alert = self.repo.add_if_new(Alert(type=type_, severity=severity, title=title[:200], message=message,
                                           dedupe_key=dedupe_key, payload=payload or {}))
        self.db.commit()
        return alert
