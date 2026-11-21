"""Idempotent background monitoring. Every alert has a dedupe_key, so reruns never duplicate."""
import logging
from datetime import date, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Alert, User
from app.repositories.planning import AlertRepo
from app.services.anomaly import AnomalyService
from app.services.budgets import BudgetService
from app.services.goals import GoalService
from app.services.insights import InsightService
from app.utils.periods import label

log = logging.getLogger(__name__)
ADVISORY_LOCK_ID = 7_301_001


class MonitoringService:
    def __init__(self, db: Session, user: User, today: date | None = None) -> None:
        self.db, self.user = db, user
        self.today = today or date.today()
        self.alerts = AlertRepo(db, user.id)

    def run(self) -> dict[str, int]:
        created = {"unusual": 0, "budget": 0, "goal": 0, "insight": 0}
        before = {a for a in self._keys()}
        AnomalyService(self.db, self.user, self.today).detect(self.today - timedelta(days=30), self.today)
        self._budget_alerts()
        self._goal_alerts()
        self._monthly_insight()
        self.db.commit()
        for key in set(self._keys()) - before:
            bucket = ("unusual" if key.startswith("unusual") else "budget" if key.startswith("budget")
                      else "goal" if key.startswith("goal") else "insight")
            created[bucket] += 1
        return created

    def _keys(self) -> list[str]:
        return list(self.db.scalars(select(Alert.dedupe_key).where(Alert.user_id == self.user.id)))

    def _budget_alerts(self) -> None:
        month = label(self.today)
        for status in BudgetService(self.db, self.user, self.today).all_status(month):
            for item in status["items"]:
                base = f"{status['budget_id']}:{item['category_id']}:{month}"
                if item["state"] == "exceeded":
                    self.alerts.add_if_new(Alert(
                        type="BUDGET_EXCEEDED", severity="critical", dedupe_key=f"budget_exceeded:{base}",
                        title=f"{item['category']} budget exceeded",
                        message=f"You have spent {item['spent']} of {item['limit']} ({item['used_pct']}%) "
                                f"on {item['category']} in {month}.",
                        payload={"budget_id": status["budget_id"], "category": item["category"]}))
                elif item["state"] == "warning":
                    self.alerts.add_if_new(Alert(
                        type="BUDGET_WARNING", severity="warning", dedupe_key=f"budget_warning:{base}",
                        title=f"{item['category']} budget almost used",
                        message=f"You have used {item['used_pct']}% of your {item['category']} budget "
                                f"in {month} ({item['remaining']} remaining).",
                        payload={"budget_id": status["budget_id"], "category": item["category"]}))

    def _goal_alerts(self) -> None:
        month = label(self.today)
        for p in GoalService(self.db, self.user, self.today).all_progress("active"):
            if p["pace"] == "behind":
                self.alerts.add_if_new(Alert(
                    type="GOAL_BEHIND", severity="warning", dedupe_key=f"goal_behind:{p['goal_id']}:{month}",
                    title=f"Goal '{p['name']}' is behind schedule",
                    message=f"You need to save about {p['required_monthly']} per month, but your recent "
                            f"average net saving is {p['avg_monthly_net']}.",
                    payload={"goal_id": p["goal_id"]}))

    def _monthly_insight(self) -> None:
        svc = InsightService(self.db, self.user, self.today)
        period = svc.previous_month_label()
        if not svc.has_data(period) or self.alerts.exists(f"monthly_insight:{period}"):
            return
        insight = svc.generate(period)
        if insight:
            self.alerts.add_if_new(Alert(type="MONTHLY_INSIGHT", severity="info",
                                         dedupe_key=f"monthly_insight:{period}", title=insight.title,
                                         message=insight.body, payload={"period": period}))


def run_all_users(factory: sessionmaker[Session], today: date | None = None) -> dict[str, int]:
    """Scheduler entry point. A Postgres advisory lock keeps multiple instances from racing."""
    totals = {"users": 0, "unusual": 0, "budget": 0, "goal": 0, "insight": 0}
    with factory() as lock_db:
        if not lock_db.scalar(text("SELECT pg_try_advisory_lock(:id)"), {"id": ADVISORY_LOCK_ID}):
            log.info("monitoring_skipped_lock_held")
            return totals
        try:
            ids = list(lock_db.scalars(select(User.id).where(User.is_active.is_(True))))
            for uid in ids:
                with factory() as db:
                    user = db.get(User, uid)
                    try:
                        res = MonitoringService(db, user, today).run()  # type: ignore[arg-type]
                    except Exception:  # one bad user must not stop the sweep
                        db.rollback()
                        log.exception("monitoring_user_failed", extra={"user_id": uid})
                        continue
                    totals["users"] += 1
                    for k, v in res.items():
                        totals[k] += v
        finally:
            lock_db.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": ADVISORY_LOCK_ID})
            lock_db.commit()
    log.info("monitoring_finished", extra=totals)
    return totals
