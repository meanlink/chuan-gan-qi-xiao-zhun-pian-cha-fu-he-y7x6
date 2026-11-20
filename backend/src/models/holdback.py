from sqlalchemy import String, JSON, Double, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Holdback(Base):
    __tablename__ = 'holdbacks'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey('datasets.id'))
    records: Mapped[list] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default='sealed')
    case_id: Mapped[int | None] = mapped_column(ForeignKey('validation_cases.id'), nullable=True)
    created_at: Mapped[float] = mapped_column(Double)
