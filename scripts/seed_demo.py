"""Explicit DEVELOPMENT-ONLY demo data:  python -m scripts.seed_demo
Creates demo@example.com / DemoPass123 with ~3 months of transactions. Refuses to run in production."""
import random
from datetime import date, timedelta
from decimal import Decimal

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models import Account, Transaction, User
from app.core.security import hash_password
from app.services.category_data import ensure_system_categories
from app.services.categorization import CategorizationService
from app.services.anomaly import AnomalyService
from app.services.transactions import make_fingerprint
from app.utils.text import normalize_merchant
from sqlalchemy import select


def main() -> None:
    if get_settings().is_production:
        raise SystemExit("Refusing to seed demo data in production")
    rnd = random.Random(42)
    with get_sessionmaker()() as db:
        ensure_system_categories(db)
        if db.scalar(select(User).where(User.email == "demo@example.com")):
            raise SystemExit("Demo user already exists")
        user = User(email="demo@example.com", hashed_password=hash_password("DemoPass123"), full_name="Demo User")
        db.add(user)
        db.flush()
        acc = Account(user_id=user.id, name="Demo Checking", type="checking", currency="USD")
        db.add(acc)
        db.flush()
        today = date.today()
        rows = []
        for m in range(3):
            base = (today.replace(day=1) - timedelta(days=30 * m)).replace(day=1)
            rows.append((base + timedelta(days=1), "income", Decimal("3200"), "Payroll ACME Inc"))
            rows.append((base + timedelta(days=2), "expense", Decimal("1100"), "Rent landlord"))
            rows.append((base + timedelta(days=4), "expense", Decimal("15.99"), "Netflix subscription"))
            for d in range(8):
                rows.append((base + timedelta(days=3 + d * 3), "expense", Decimal(rnd.randint(12, 45)), "Local Cafe"))
                rows.append((base + timedelta(days=5 + d * 3), "expense", Decimal(rnd.randint(40, 120)), "Whole Foods grocery"))
        rows.append((today, "expense", Decimal("480"), "Local Cafe"))
        ids = []
        for i, (d, direction, amount, desc) in enumerate(rows):
            if d > today:
                continue
            tx = Transaction(user_id=user.id, account_id=acc.id, posted_on=d, amount=amount, direction=direction,
                             currency="USD", description=desc, merchant=normalize_merchant(desc),
                             fingerprint=make_fingerprint(acc.id, d, amount, direction, desc, i))
            db.add(tx)
            db.flush()
            ids.append(tx.id)
        CategorizationService(db, user).categorize_ids(ids)
        AnomalyService(db, user).detect_for_ids(ids)
        db.commit()
        print("Seeded demo@example.com / DemoPass123")


if __name__ == "__main__":
    main()
