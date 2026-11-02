from sqlalchemy import text

from app.db.base import Base
from app.db.models import AutomationAuditLog, BotAccount, Order, ServiceCatalog, User
from app.db.session import SessionLocal, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                "is_admin BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )


if __name__ == "__main__":
    init_db()
    print("database_schema_initialized=true")
