from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal


SERVICE_SEED = [
    {
        "name": "Premium Global Follows",
        "type": "social_distribution",
        "price_per_hundred": 1.25,
        "description": "Managed premium follow delivery across global audiences.",
    },
    {
        "name": "Instagram Story Likes",
        "type": "social_distribution",
        "price_per_hundred": 1.40,
        "description": "Category for story engagement actions on Instagram.",
    },
    {
        "name": "Facebook Profile Visits",
        "type": "social_distribution",
        "price_per_hundred": 1.10,
        "description": "Profile and content visit actions for Facebook campaigns.",
    },
    {
        "name": "TikTok Content Views",
        "type": "social_distribution",
        "price_per_hundred": 1.35,
        "description": "View-based distribution tasks for TikTok content exposure.",
    },
    {
        "name": "Discord Community Pulse",
        "type": "social_distribution",
        "price_per_hundred": 1.55,
        "description": "Community reach and engagement actions for Discord channels.",
    },
    {
        "name": "Web Scrape Audit",
        "type": "scrape",
        "price_per_hundred": 1.80,
        "description": "Standard scrape and page validation processing for URLs.",
    },
    {
        "name": "API Contract Check",
        "type": "api_test",
        "price_per_hundred": 1.95,
        "description": "API validation and health-check workflows for test environments.",
    },
]


def seed_service_catalog() -> int:
    db: Session = SessionLocal()
    try:
        count = db.execute(text("SELECT COUNT(*) FROM service_catalog")).scalar_one()
        if count > 0:
            return int(count)

        for service in SERVICE_SEED:
            db.execute(
                text(
                    """
                    INSERT INTO service_catalog (name, type, price_per_hundred, description)
                    VALUES (:name, :type, :price_per_hundred, :description)
                    """
                ),
                {
                    "name": service["name"],
                    "type": service["type"],
                    "price_per_hundred": service["price_per_hundred"],
                    "description": service["description"],
                },
            )
        db.commit()
        return len(SERVICE_SEED)
    finally:
        db.close()


if __name__ == "__main__":
    seed_service_catalog()
    print("Service catalog seeded successfully.")
