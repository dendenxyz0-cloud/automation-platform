from fastapi import FastAPI
from app.api.routes.orders import router as orders_router

app = FastAPI(title="Automation Platform API", version="1.0.0")

app.include_router(orders_router, prefix="/api/v1")
