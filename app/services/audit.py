from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import AutomationAuditLog


_SECRET_KEYS = {"password", "token", "secret", "credentials", "credentials_encrypted", "cookies"}


def _safe_details(details: Optional[dict[str, Any]]) -> Optional[str]:
    if not details:
        return None
    safe = {key: value for key, value in details.items() if key.lower() not in _SECRET_KEYS}
    return json.dumps(safe, default=str, separators=(",", ":"))


def record_audit_event(
    db: Session,
    *,
    event_type: str,
    status: str,
    platform: str,
    order_id: Optional[int] = None,
    account_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    db.add(
        AutomationAuditLog(
            order_id=order_id,
            account_id=account_id,
            platform=platform,
            event_type=event_type,
            status=status,
            details=_safe_details(details),
        )
    )
    db.commit()
