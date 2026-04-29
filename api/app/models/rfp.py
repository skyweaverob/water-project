import uuid
from datetime import date
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Rfp(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "rfps"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("facility_profiles.id", ondelete="CASCADE"), index=True)
    chemical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), default="draft")  # draft | published | closed | awarded
    quantity_kg_annual: Mapped[float | None] = mapped_column(Float)
    contract_term_months: Mapped[int | None] = mapped_column(Integer)
    delivery_window_days: Mapped[int | None] = mapped_column(Integer)
    spec_concentration_pct: Mapped[float | None] = mapped_column(Float)
    spec_purity_standard: Mapped[str | None] = mapped_column(String(100))  # e.g. "NSF/ANSI 60"
    resilience_clauses: Mapped[dict | None] = mapped_column(JSONB)
    evaluation_weights: Mapped[dict | None] = mapped_column(JSONB)
    boilerplate_terms: Mapped[str | None] = mapped_column(Text)
    generated_docx_path: Mapped[str | None] = mapped_column(String(400))
    bid_due_date: Mapped[date | None] = mapped_column(Date)
    award_date: Mapped[date | None] = mapped_column(Date)

    bids: Mapped[list["Bid"]] = relationship(back_populates="rfp", cascade="all, delete-orphan")


class Bid(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bids"

    rfp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rfps.id", ondelete="CASCADE"), index=True)
    supplier_name: Mapped[str] = mapped_column(String(200))
    supplier_contact_email: Mapped[str | None] = mapped_column(String(200))
    submitted_at: Mapped[date | None] = mapped_column(Date)
    raw_document_path: Mapped[str | None] = mapped_column(String(400))
    extracted_terms: Mapped[dict | None] = mapped_column(JSONB)
    is_conforming: Mapped[bool] = mapped_column(Boolean, default=True)
    nonconformance_notes: Mapped[str | None] = mapped_column(Text)
    normalized_price_per_kg_active: Mapped[float | None] = mapped_column(Float)
    risk_adjusted_score: Mapped[float | None] = mapped_column(Float)
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False)

    rfp: Mapped[Rfp] = relationship(back_populates="bids")
    line_items: Mapped[list["BidLineItem"]] = relationship(back_populates="bid", cascade="all, delete-orphan")


class BidLineItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bid_line_items"

    bid_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bids.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(400))
    unit: Mapped[str] = mapped_column(String(40))  # kg, gal, ton, lb
    unit_price: Mapped[float] = mapped_column(Float)
    delivered_concentration_pct: Mapped[float | None] = mapped_column(Float)
    freight_terms: Mapped[str | None] = mapped_column(String(80))

    bid: Mapped[Bid] = relationship(back_populates="line_items")


class AwardMemo(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "award_memos"

    rfp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rfps.id", ondelete="CASCADE"), index=True, unique=True)
    recommended_bid_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bids.id"))
    memo_format: Mapped[str] = mapped_column(String(40))  # municipal | corporate
    pdf_path: Mapped[str | None] = mapped_column(String(400))
    rationale: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSONB)
