import uuid
from datetime import date
from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TimestampMixin, UUIDMixin

EMBED_DIM = 1024  # voyage-3 default


class Chemical(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chemicals"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    cas_number: Mapped[str | None] = mapped_column(String(40), index=True)
    molecular_formula: Mapped[str | None] = mapped_column(String(100))
    physical_state: Mapped[str | None] = mapped_column(String(60))
    shelf_life_months: Mapped[int | None] = mapped_column(Integer)
    product_family: Mapped[str | None] = mapped_column(String(120))
    water_treatment_use: Mapped[str | None] = mapped_column(Text)
    is_direct_treatment_chemical: Mapped[bool] = mapped_column(Boolean, default=False)
    is_precursor: Mapped[bool] = mapped_column(Boolean, default=False)
    derivative_chemicals: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    pct_consumption_water_sector: Mapped[float | None] = mapped_column(Float)
    source_pdf: Mapped[str | None] = mapped_column(String(400))
    extraction_confidence: Mapped[float | None] = mapped_column(Float)

    applications: Mapped[list["Application"]] = relationship(back_populates="chemical", cascade="all, delete-orphan")
    manufacturing_locations: Mapped[list["ManufacturingLocation"]] = relationship(back_populates="chemical", cascade="all, delete-orphan")
    trade_data: Mapped[list["TradeData"]] = relationship(back_populates="chemical", cascade="all, delete-orphan")
    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(back_populates="chemical", cascade="all, delete-orphan")
    disruption_events: Mapped[list["DisruptionEvent"]] = relationship(back_populates="chemical", cascade="all, delete-orphan")
    chunks: Mapped[list["FactSheetChunk"]] = relationship(back_populates="chemical", cascade="all, delete-orphan")


class Application(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "applications"

    chemical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id", ondelete="CASCADE"), index=True)
    application_type: Mapped[str] = mapped_column(String(40))  # water_treatment | other
    description: Mapped[str] = mapped_column(Text)

    chemical: Mapped[Chemical] = relationship(back_populates="applications")


class ManufacturingLocation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "manufacturing_locations"

    chemical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id", ondelete="CASCADE"), index=True)
    country: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str | None] = mapped_column(String(80))
    facility_count: Mapped[int | None] = mapped_column(Integer)
    year: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(200))

    chemical: Mapped[Chemical] = relationship(back_populates="manufacturing_locations")


class TradeData(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "trade_data"

    chemical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    imports_kg: Mapped[float | None] = mapped_column(Float)
    exports_kg: Mapped[float | None] = mapped_column(Float)
    primary_import_partner: Mapped[str | None] = mapped_column(String(120))
    primary_export_partner: Mapped[str | None] = mapped_column(String(120))
    hts_code: Mapped[str | None] = mapped_column(String(20))
    general_duty_pct: Mapped[float | None] = mapped_column(Float)
    china_section_301_duty_pct: Mapped[float | None] = mapped_column(Float)
    special_duty_countries: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    chemical: Mapped[Chemical] = relationship(back_populates="trade_data")


class RiskAssessment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "risk_assessments"

    chemical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id", ondelete="CASCADE"), index=True)
    assessment_date: Mapped[date | None] = mapped_column(Date)
    criticality: Mapped[str | None] = mapped_column(String(40))
    likelihood: Mapped[str | None] = mapped_column(String(40))
    vulnerability: Mapped[str | None] = mapped_column(String(40))
    composite_rating: Mapped[str | None] = mapped_column(String(40))
    criticality_drivers: Mapped[str | None] = mapped_column(Text)
    likelihood_drivers: Mapped[str | None] = mapped_column(Text)
    vulnerability_drivers: Mapped[str | None] = mapped_column(Text)

    chemical: Mapped[Chemical] = relationship(back_populates="risk_assessments")


class DisruptionEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "disruption_events"

    chemical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id", ondelete="CASCADE"), index=True)
    event_date: Mapped[date | None] = mapped_column(Date)
    event_type: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    source_citation: Mapped[str | None] = mapped_column(String(400))

    chemical: Mapped[Chemical] = relationship(back_populates="disruption_events")


class SubstituteOrPrecursor(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "substitutes_and_precursors"

    chemical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id", ondelete="CASCADE"), index=True)
    related_chemical_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id", ondelete="SET NULL"))
    related_chemical_name: Mapped[str | None] = mapped_column(String(200))
    relationship_type: Mapped[str] = mapped_column(String(40))  # substitute | precursor | derivative
    notes: Mapped[str | None] = mapped_column(Text)


class FactSheetChunk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "fact_sheet_chunks"

    chemical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id", ondelete="CASCADE"), index=True)
    page_num: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM))

    chemical: Mapped[Chemical] = relationship(back_populates="chunks")
