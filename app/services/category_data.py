"""System categories and built-in merchant keywords (reference data, not demo data)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category

SYSTEM_CATEGORIES: list[tuple[str, str]] = [
    ("Food", "expense"), ("Groceries", "expense"), ("Transport", "expense"), ("Utilities", "expense"),
    ("Rent & Housing", "expense"), ("Entertainment", "expense"), ("Shopping", "expense"),
    ("Health", "expense"), ("Education", "expense"), ("Travel", "expense"),
    ("Subscriptions", "expense"), ("Fees & Charges", "expense"),
    ("Salary", "income"), ("Other Income", "income"),
]

KEYWORDS: dict[str, list[str]] = {
    "Food": ["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "kfc", "burger", "pizza", "subway",
             "doordash", "ubereats", "uber eats", "grubhub", "bakery", "diner", "dominos", "taco", "sushi"],
    "Groceries": ["grocery", "supermarket", "whole foods", "trader joe", "aldi", "kroger", "safeway",
                  "carrefour", "walmart grocery", "costco", "lidl", "tesco"],
    "Transport": ["uber", "lyft", "taxi", "metro", "fuel", "gas station", "shell", "chevron", "parking",
                  "careem", "bus pass", "train"],
    "Utilities": ["electric", "water bill", "gas bill", "internet", "broadband", "utility", "phone bill",
                  "verizon", "at&t", "comcast"],
    "Rent & Housing": ["rent", "mortgage", "landlord", "property tax", "hoa"],
    "Entertainment": ["cinema", "movie", "theatre", "concert", "steam", "playstation", "xbox", "ticketmaster"],
    "Shopping": ["amazon", "ebay", "target", "walmart", "ikea", "best buy", "mall", "zara", "h&m", "nike"],
    "Health": ["pharmacy", "clinic", "hospital", "dental", "doctor", "cvs", "walgreens", "gym", "optical"],
    "Education": ["tuition", "university", "course", "udemy", "coursera", "school", "bookstore"],
    "Travel": ["airline", "airways", "hotel", "airbnb", "booking.com", "expedia", "flight"],
    "Subscriptions": ["netflix", "spotify", "hulu", "disney+", "youtube premium", "subscription", "icloud",
                      "dropbox", "adobe", "openai", "github"],
    "Fees & Charges": ["bank fee", "service charge", "overdraft", "atm fee", "late fee", "interest charge"],
    "Salary": ["salary", "payroll", "direct deposit", "wages", "paycheck"],
    "Other Income": ["refund", "interest paid", "dividend", "cashback", "reimbursement"],
}


def ensure_system_categories(db: Session) -> None:
    existing = set(db.scalars(select(Category.name).where(Category.user_id.is_(None))))
    for name, kind in SYSTEM_CATEGORIES:
        if name not in existing:
            db.add(Category(name=name, kind=kind, is_system=True, user_id=None))
    db.commit()
