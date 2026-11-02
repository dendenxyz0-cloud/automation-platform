from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.schemas import OrderCreate, OrderResponse, ServiceResponse
from app.db.models import Order, ServiceCatalog, User
from app.tasks.orders import process_order_task

router = APIRouter(tags=["orders"])


def _order_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        service_id=order.service_id,
        target_url=order.target_url,
        quantity=order.quantity,
        status=order.status,
        created_at=order.created_at,
    )


@router.get("/services", response_model=list[ServiceResponse])
def list_services(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    services = db.query(ServiceCatalog).order_by(ServiceCatalog.name.asc()).all()
    return [
        ServiceResponse(
            id=service.id,
            name=service.name,
            type=service.type,
            price_per_hundred=float(service.price_per_hundred),
            description=service.description,
        )
        for service in services
    ]


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    orders = (
        db.query(Order)
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(100)
        .all()
    )
    return [_order_response(order) for order in orders]


@router.post("/orders", status_code=status.HTTP_201_CREATED, response_model=OrderResponse)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = db.query(ServiceCatalog).filter(ServiceCatalog.id == payload.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    order = Order(
        user_id=user.id,
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
    return _order_response(order)
