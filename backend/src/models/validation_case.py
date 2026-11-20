from sqlalchemy import String, JSON, Double, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class ValidationCase(Base):
    __tablename__ = 'validation_cases'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'))
    tolerances: Mapped[dict] = mapped_column(JSON, default=dict)
    locked_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    holdback_id: Mapped[int | None] = mapped_column(ForeignKey('holdbacks.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='open')
    verdict: Mapped[str] = mapped_column(String(20), default='')
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(String(1000), default='')
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[float] = mapped_column(Double)
    finished_at: Mapped[float | None] = mapped_column(Double, nullable=True)
