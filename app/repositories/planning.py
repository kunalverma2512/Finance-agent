from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update

from app.models import AgentRun, Alert, Budget, ChatMessage, FinancialGoal, Insight
from app.repositories.base import Repo


class BudgetRepo(Repo):
    def get(self, budget_id: int) -> Budget | None:
        return self.db.scalar(select(Budget).where(Budget.id == budget_id, Budget.user_id == self.user_id))

    def get_by_name(self, name: str) -> Budget | None:
        return self.db.scalar(select(Budget).where(Budget.user_id == self.user_id,
                                                    func.lower(Budget.name) == name.lower()))

    def list(self, status: str | None = None) -> list[Budget]:
        q = select(Budget).where(Budget.user_id == self.user_id).order_by(Budget.name)
        if status:
            q = q.where(Budget.status == status)
        return list(self.db.scalars(q))

    def add(self, budget: Budget) -> Budget:
        budget.user_id = self.user_id
        for item in budget.items:
            item.user_id = self.user_id
        self.db.add(budget)
        self.db.flush()
        return budget

    def delete(self, budget: Budget) -> None:
        self.db.delete(budget)
        self.db.flush()


class GoalRepo(Repo):
    def get(self, goal_id: int) -> FinancialGoal | None:
        return self.db.scalar(select(FinancialGoal).where(FinancialGoal.id == goal_id,
                                                           FinancialGoal.user_id == self.user_id))

    def get_by_name(self, name: str) -> FinancialGoal | None:
        return self.db.scalar(select(FinancialGoal).where(FinancialGoal.user_id == self.user_id,
                                                           func.lower(FinancialGoal.name) == name.lower()))

    def list(self, status: str | None = None) -> list[FinancialGoal]:
        q = select(FinancialGoal).where(FinancialGoal.user_id == self.user_id).order_by(FinancialGoal.id)
        if status:
            q = q.where(FinancialGoal.status == status)
        return list(self.db.scalars(q))

    def add(self, goal: FinancialGoal) -> FinancialGoal:
        goal.user_id = self.user_id
        self.db.add(goal)
        self.db.flush()
        return goal

    def delete(self, goal: FinancialGoal) -> None:
        self.db.delete(goal)
        self.db.flush()


class AlertRepo(Repo):
    def get(self, alert_id: int) -> Alert | None:
        return self.db.scalar(select(Alert).where(Alert.id == alert_id, Alert.user_id == self.user_id))

    def exists(self, dedupe_key: str) -> bool:
        return self.db.scalar(select(Alert.id).where(Alert.user_id == self.user_id,
                                                      Alert.dedupe_key == dedupe_key)) is not None

    def page(self, status: str | None, limit: int, offset: int) -> tuple[list[Alert], int]:
        q = select(Alert).where(Alert.user_id == self.user_id)
        if status:
            q = q.where(Alert.status == status)
        total = self.db.scalar(select(func.count()).select_from(q.subquery())) or 0
        rows = self.db.scalars(q.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit).offset(offset))
        return list(rows), total

    def unread_count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Alert)
                              .where(Alert.user_id == self.user_id, Alert.status == "unread")) or 0

    def add_if_new(self, alert: Alert) -> Alert | None:
        """Insert unless an alert with the same dedupe_key exists (idempotent monitoring)."""
        if self.exists(alert.dedupe_key):
            return None
        alert.user_id = self.user_id
        self.db.add(alert)
        self.db.flush()
        return alert

    def mark_all_read(self, when: datetime) -> int:
        res = self.db.execute(update(Alert).where(Alert.user_id == self.user_id, Alert.status == "unread")
                              .values(status="read", read_at=when))
        return res.rowcount or 0


class InsightRepo(Repo):
    def get(self, kind: str, period: str) -> Insight | None:
        return self.db.scalar(select(Insight).where(Insight.user_id == self.user_id, Insight.kind == kind,
                                                     Insight.period == period))

    def list(self, limit: int = 12) -> list[Insight]:
        return list(self.db.scalars(select(Insight).where(Insight.user_id == self.user_id)
                                    .order_by(Insight.period.desc(), Insight.id.desc()).limit(limit)))

    def upsert(self, kind: str, period: str, title: str, body: str, data: dict[str, Any]) -> Insight:
        row = self.get(kind, period)
        if row:
            row.title, row.body, row.data = title, body, data
        else:
            row = Insight(user_id=self.user_id, kind=kind, period=period, title=title, body=body, data=data)
            self.db.add(row)
        self.db.flush()
        return row


class AgentRunRepo(Repo):
    def get(self, run_id: str) -> AgentRun | None:
        return self.db.scalar(select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == self.user_id))

    def add(self, run: AgentRun) -> AgentRun:
        run.user_id = self.user_id
        self.db.add(run)
        self.db.flush()
        return run

    def recent_messages(self, limit: int) -> list[ChatMessage]:
        rows = self.db.scalars(select(ChatMessage).where(ChatMessage.user_id == self.user_id)
                               .order_by(ChatMessage.id.desc()).limit(limit))
        return list(reversed(list(rows)))

    def add_message(self, role: str, content: str, run_id: str | None) -> ChatMessage:
        msg = ChatMessage(user_id=self.user_id, role=role, content=content, run_id=run_id)
        self.db.add(msg)
        self.db.flush()
        return msg
