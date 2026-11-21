from datetime import date
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

T = TypeVar("T")


def _upper(v: str) -> str:
    return v.upper()


Currency = Annotated[str, StringConstraints(pattern=r"^[A-Za-z]{3}$"), AfterValidator(_upper)]
Money = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
MoneyNonNeg = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Message(BaseModel):
    message: str


__all__ = ["Currency", "Money", "MoneyNonNeg", "ORM", "Page", "Message", "date"]
