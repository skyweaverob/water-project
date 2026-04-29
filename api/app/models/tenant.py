import uuid
from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Tenant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    vertical: Mapped[str] = mapped_column(String(40), default="municipal")  # municipal | industrial
    plan: Mapped[str] = mapped_column(String(40), default="single_facility")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(120))
    seat_limit: Mapped[int] = mapped_column(Integer, default=5)
    facility_limit: Mapped[int] = mapped_column(Integer, default=1)

    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    facilities: Mapped[list["FacilityProfile"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class VerticalConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vertical_config"

    vertical: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    terminology: Mapped[dict] = mapped_column(JSONB, default=dict)
    report_template_id: Mapped[str | None] = mapped_column(String(120))
    rfp_boilerplate: Mapped[str | None] = mapped_column(Text)
    memo_format: Mapped[str | None] = mapped_column(String(40))


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    clerk_user_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(40), default="member")  # owner | admin | member

    tenant: Mapped[Tenant] = relationship(back_populates="users")


class FacilityProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "facility_profiles"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[str] = mapped_column(String(40))  # drinking_water | wastewater | industrial_pretreatment
    flow_mgd: Mapped[float | None] = mapped_column(Float)
    treatment_processes: Mapped[list[str] | None] = mapped_column(JSONB)
    location_state: Mapped[str | None] = mapped_column(String(40))
    location_city: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    tenant: Mapped[Tenant] = relationship(back_populates="facilities")
    portfolio_chemicals: Mapped[list["PortfolioChemical"]] = relationship(back_populates="facility", cascade="all, delete-orphan")


class PortfolioChemical(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "portfolio_chemicals"
    __table_args__ = (UniqueConstraint("facility_id", "chemical_id"),)

    facility_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("facility_profiles.id", ondelete="CASCADE"), index=True)
    chemical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chemicals.id", ondelete="CASCADE"), index=True)
    annual_demand_kg: Mapped[float | None] = mapped_column(Float)
    typical_dose_mgL: Mapped[float | None] = mapped_column(Float)
    current_supplier: Mapped[str | None] = mapped_column(String(200))
    current_price_per_kg: Mapped[float | None] = mapped_column(Float)
    contract_end_date: Mapped[str | None] = mapped_column(String(40))

    facility: Mapped[FacilityProfile] = relationship(back_populates="portfolio_chemicals")
