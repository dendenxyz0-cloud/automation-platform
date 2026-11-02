from __future__ import annotations

import json
from typing import Any

from sqlalchemy import or_


def platform_status_summary(db) -> dict[str, Any]:
    from app.db.models import BotAccount

    rows = db.query(BotAccount).filter(BotAccount.status.in_(["Active", "Flagged", "Dead", "In-Use"])).all()
    summary = {"Active": 0, "Flagged": 0, "Dead": 0, "In-Use": 0}
    for row in rows:
        status = row.status
        if status in summary:
            summary[status] += 1
    return summary


def latest_audit_rows(db, limit: int = 20):
    from app.db.models import AutomationAuditLog

    return db.query(AutomationAuditLog).order_by(AutomationAuditLog.created_at.desc()).limit(limit).all()
