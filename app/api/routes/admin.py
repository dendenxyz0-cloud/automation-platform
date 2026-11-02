from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import AutomationAuditLog, BotAccount, User

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


@router.get("/metrics")
def metrics(
    db: Session = Depends(get_db),
    _admin: User = Depends(_require_admin),
):
    counts = dict(
        db.query(BotAccount.status, func.count(BotAccount.id))
        .group_by(BotAccount.status)
        .all()
    )
    audits = (
        db.query(AutomationAuditLog)
        .order_by(AutomationAuditLog.created_at.desc(), AutomationAuditLog.id.desc())
        .limit(20)
        .all()
    )
    return {
        "accounts": {
            "active": counts.get("Active", 0),
            "flagged": counts.get("Flagged", 0),
            "in_use": counts.get("In-Use", 0),
            "dead": counts.get("Dead", 0),
        },
        "audit_logs": [
            {
                "id": entry.id,
                "event_type": entry.event_type,
                "status": entry.status,
                "platform": entry.platform,
                "account_id": entry.account_id,
                "created_at": entry.created_at,
            }
            for entry in audits
        ],
    }
