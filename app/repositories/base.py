from sqlalchemy.orm import Session


class Repo:
    """All repositories are bound to ONE user: every query is scoped by user_id."""

    def __init__(self, db: Session, user_id: int) -> None:
        self.db = db
        self.user_id = user_id
