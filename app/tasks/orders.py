from typing import Any, Dict, Optional

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.models import Order
from app.db.session import SessionLocal
from app.services.browser_runner import run_headless_visit


def _set_order_status(order_id: int, status: str) -> None:
    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == order_id).one_or_none()
        if order is None:
            raise RuntimeError(f"Order {order_id} not found")
        order.status = status
        db.commit()


@shared_task(
    bind=True,
    name="process_order_task",
    autoretry_for=(Exception,),
    retry_backoff=5,
    max_retries=3,
)
def process_order_task(self, order_id: int, target_url: str, proxy: Optional[dict] = None):
    try:
        _set_order_status(order_id, "Processing")

        result = run_headless_visit(target_url=target_url, proxy=proxy)

        if not result["success"]:
            raise RuntimeError(result.get("error", "Browser task failed"))

        _set_order_status(order_id, "Completed")
        return {
            "order_id": order_id,
            "status": "Completed",
            "details": result,
        }

    except Exception as exc:
        try:
            _set_order_status(order_id, "Cancelled")
        except Exception:
            pass
        raise exc
