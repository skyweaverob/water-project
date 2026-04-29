import uuid
from datetime import date
from sqlalchemy import Date, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class RiskScore(Base, UUIDMixin, TimestampMixin):
    """Daily risk score row.

    Three valid shapes:
      - facility rollup:  facility_id set, chemical_id null  (chart line)
      - per-chemical:     facility_id null, chemical_id set  (drill-down)
      - tenant rollup:    facility_id null, chemical_id null (multi-facility tenants)
    """
    __tablename__ = "risk_scores"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("facility_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    chemical_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id"), nullable=True, index=True)
    score_date: Mapped[date] = mapped_column(Date, index=True)
    composite_score: Mapped[float] = mapped_column(Float)  # 0-100
    composite_band: Mapped[str] = mapped_column(String(40))  # low | moderate-low | moderate | moderate-high | high
    components: Mapped[dict | None] = mapped_column(JSONB)


class RiskAlert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "risk_alerts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("facility_profiles.id", ondelete="CASCADE"), nullable=True)
    chemical_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String(40))  # info | watch | warning
    headline: Mapped[str] = mapped_column(String(300))
    body: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(500))
    triggered_at: Mapped[date] = mapped_column(Date, index=True)
    acknowledged: Mapped[bool] = mapped_column(default=False)
