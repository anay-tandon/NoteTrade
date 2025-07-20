from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

# ───────── Transaction model ─────────
class Transaction(SQLModel, table=True):
    """
    Records each sale / purchase of a note.
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    note_id: int                       # FK → Note.id
    buyer: str                         # username / identifier of buyer
    price: float                       # price paid
    timestamp: datetime = Field(default_factory=datetime.utcnow)
from typing import Optional
from sqlmodel import SQLModel, Field


class Note(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    subject: str
    category: str
    price: float
    file_path: str