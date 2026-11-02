# app/db/init_db.py
from app.db.base import Base
from app.db.models import AutomationAuditLog, BotAccount, Order, ServiceCatalog, User
from app.db.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
