import uuid
from sqlalchemy import ForeignKey, String, Text, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class QnaQuery(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "qna_queries"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSONB)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    model_used: Mapped[str | None] = mapped_column(String(80))
