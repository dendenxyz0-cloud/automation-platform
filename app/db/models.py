from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Boolean,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    is_admin = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    orders = relationship("Order", back_populates="user")


class ServiceCatalog(Base):
    __tablename__ = "service_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    type = Column(String(50), nullable=False)
    price_per_hundred = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    orders = relationship("Order", back_populates="service")

    __table_args__ = (
        CheckConstraint(
            "type IN ('scrape', 'api_test', 'social_distribution')",
            name="ck_service_type",
        ),
    )


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("service_catalog.id"), nullable=False, index=True)
    target_url = Column(String(2048), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="Pending", server_default="Pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="orders")
    service = relationship("ServiceCatalog", back_populates="orders")

    __table_args__ = (
        CheckConstraint(
            "status IN ('Pending', 'Processing', 'Completed', 'Cancelled')",
            name="ck_order_status",
        ),
        CheckConstraint("quantity > 0", name="ck_order_quantity_positive"),
    )


class BotPlatform(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    DISCORD = "discord"
    X = "x"


class BotAccountStatus(str, Enum):
    ACTIVE = "Active"
    FLAGGED = "Flagged"
    IN_USE = "In-Use"
    DEAD = "Dead"


class BotAccount(Base):
    __tablename__ = "bot_accounts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(32), nullable=False, index=True)
    username = Column(String(255), nullable=False, index=True)
    # These values must be encrypted before persistence by the application layer.
    # They are intentionally opaque to platform handlers and are never logged.
    credentials_encrypted = Column(Text, nullable=False)
    session_cookies = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default=BotAccountStatus.ACTIVE.value,
                    server_default=BotAccountStatus.ACTIVE.value, index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "platform IN ('facebook', 'instagram', 'tiktok', 'discord', 'x')",
            name="ck_bot_account_platform",
        ),
        CheckConstraint(
            "status IN ('Active', 'Flagged', 'In-Use', 'Dead')",
            name="ck_bot_account_status",
        ),
    )


class AutomationAuditLog(Base):
    __tablename__ = "automation_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    account_id = Column(Integer, ForeignKey("bot_accounts.id"), nullable=True, index=True)
    platform = Column(String(32), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
