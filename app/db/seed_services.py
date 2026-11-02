from __future__ import annotations

from decimal import Decimal

from app.db.models import ServiceCatalog
from app.db.session import SessionLocal


DEFAULT_SERVICES = (
    {
        "name": "Automated Profile Status Verification",
        "type": "scrape",
        "price_per_hundred": Decimal("1.00"),
        "description": "Authorized status checks against approved fixtures or APIs.",
    },
    {
        "name": "Cross-Platform Media Performance Test",
        "type": "social_distribution",
        "price_per_hundred": Decimal("1.50"),
        "description": "Staging-only media workflow validation across approved integrations.",
    },
    {
        "name": "Distributed Response Monitoring Sync",
        "type": "api_test",
        "price_per_hundred": Decimal("0.75"),
        "description": "Distributed response and availability checks for owned services.",
    },
)


def seed_services() -> int:
    with SessionLocal() as db:
        if db.query(ServiceCatalog).count() > 0:
            return 0
        db.add_all(ServiceCatalog(**service) for service in DEFAULT_SERVICES)
        db.commit()
        return len(DEFAULT_SERVICES)


if __name__ == "__main__":
    print(f"seeded_services={seed_services()}")
