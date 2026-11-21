from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import DB, CurrentUser
from app.schemas.planning import (BudgetIn, BudgetOut, BudgetUpdate, ContributionIn, GoalIn, GoalOut,
                                  GoalUpdate)
from app.services.analytics import AnalyticsService
from app.services.budgets import BudgetService
from app.services.goals import GoalService
from app.services.insights import InsightService
from app.services.monitoring import MonitoringService

router = APIRouter()
MonthQ = Annotated[str | None, Query(pattern=r"^(\d{4}-(0[1-9]|1[0-2])|this_month|last_month)$")]


@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(user: CurrentUser, db: DB, status: Literal["active", "archived"] | None = None):
    return BudgetService(db, user).repo.list(status)


@router.post("/budgets", response_model=BudgetOut, status_code=201)
def create_budget(data: BudgetIn, user: CurrentUser, db: DB):
    return BudgetService(db, user).create(data)


@router.get("/budgets/status", response_model=list[dict])
def all_budget_status(user: CurrentUser, db: DB, month: MonthQ = None):
    return BudgetService(db, user).all_status(month)


@router.get("/budgets/{budget_id}", response_model=BudgetOut)
def get_budget(budget_id: int, user: CurrentUser, db: DB):
    return BudgetService(db, user).get(budget_id)


@router.get("/budgets/{budget_id}/status", response_model=dict)
def budget_status(budget_id: int, user: CurrentUser, db: DB, month: MonthQ = None):
    svc = BudgetService(db, user)
    return svc.status(svc.get(budget_id), month)


@router.patch("/budgets/{budget_id}", response_model=BudgetOut)
def update_budget(budget_id: int, data: BudgetUpdate, user: CurrentUser, db: DB):
    return BudgetService(db, user).update(budget_id, data)


@router.delete("/budgets/{budget_id}", status_code=204)
def delete_budget(budget_id: int, user: CurrentUser, db: DB, hard: bool = False):
    BudgetService(db, user).delete(budget_id, hard)


@router.get("/goals", response_model=list[dict])
def list_goals(user: CurrentUser, db: DB):
    return GoalService(db, user).all_progress()


@router.post("/goals", response_model=GoalOut, status_code=201)
def create_goal(data: GoalIn, user: CurrentUser, db: DB):
    return GoalService(db, user).create(data)


@router.get("/goals/{goal_id}", response_model=dict)
def get_goal(goal_id: int, user: CurrentUser, db: DB):
    svc = GoalService(db, user)
    return svc.all_progress_one(goal_id)


@router.patch("/goals/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, data: GoalUpdate, user: CurrentUser, db: DB):
    return GoalService(db, user).update(goal_id, data)


@router.post("/goals/{goal_id}/contributions", response_model=GoalOut)
def contribute(goal_id: int, data: ContributionIn, user: CurrentUser, db: DB):
    return GoalService(db, user).contribute(goal_id, data.amount)


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: int, user: CurrentUser, db: DB):
    GoalService(db, user).delete(goal_id)


@router.get("/analytics/summary", response_model=dict)
def analytics_summary(user: CurrentUser, db: DB, month: MonthQ = None):
    return AnalyticsService(db, user).summary(month)


@router.get("/analytics/categories", response_model=list[dict])
def analytics_categories(user: CurrentUser, db: DB, month: MonthQ = None):
    return AnalyticsService(db, user).categories(month)


@router.get("/analytics/monthly", response_model=list[dict])
def analytics_monthly(user: CurrentUser, db: DB, months: Annotated[int, Query(ge=1, le=24)] = 6):
    return AnalyticsService(db, user).monthly(months)


@router.get("/analytics/anomalies", response_model=list[dict])
def analytics_anomalies(user: CurrentUser, db: DB, days: Annotated[int, Query(ge=1, le=365)] = 90):
    from datetime import date, timedelta

    from app.services.anomaly import AnomalyService
    today = date.today()
    return AnomalyService(db, user).detect(today - timedelta(days=days), today, persist=False)


@router.get("/insights", response_model=list[dict])
def list_insights(user: CurrentUser, db: DB):
    return [{"id": i.id, "kind": i.kind, "period": i.period, "title": i.title, "body": i.body,
             "data": i.data} for i in InsightService(db, user).list()]


@router.post("/insights/generate", response_model=dict)
def generate_insight(user: CurrentUser, db: DB, month: MonthQ = "last_month"):
    from app.core.errors import NotFoundError
    insight = InsightService(db, user).generate(month)
    if insight is None:
        raise NotFoundError("No transactions in that month to analyse", code="NO_DATA")
    return {"id": insight.id, "period": insight.period, "title": insight.title, "body": insight.body,
            "data": insight.data}


@router.post("/monitoring/run", response_model=dict)
def run_monitoring(user: CurrentUser, db: DB):
    return MonitoringService(db, user).run()
