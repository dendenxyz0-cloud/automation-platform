from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import OrderCreate, OrderResponse
from app.db.models import Order, ServiceCatalog, User
from app.tasks.orders import process_order_task

router = APIRouter(tags=["orders"])


@router.post("/orders", status_code=status.HTTP_201_CREATED, response_model=OrderResponse)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    service = db.query(ServiceCatalog).filter(ServiceCatalog.id == payload.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    order = Order(
        user_id=payload.user_id,
        service_id=payload.service_id,
        target_url=str(payload.target_url),
        quantity=payload.quantity,
        status="Pending",
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    task_payload = {
        "order_id": order.id,
        "platform": payload.platform,
        "action_type": payload.action_type,
        "target_url": order.target_url,
        "proxy": payload.proxy.model_dump() if payload.proxy else None,
    }

    process_order_task.delay(**task_payload)

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        service_id=order.service_id,
        target_url=order.target_url,
        quantity=order.quantity,
        status=order.status,
    )
