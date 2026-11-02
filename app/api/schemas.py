from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuthCredentials(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class OrderCreate(BaseModel):
    service_id: int
    platform: str = Field(default="test", pattern="^(facebook|instagram|tiktok|discord|x|test)$")
    action_type: str = Field(default="navigate", min_length=1, max_length=64)
    target_url: str
    quantity: int = Field(default=1, ge=1, le=10000)


class OrderResponse(BaseModel):
    id: int
    user_id: int
    service_id: int
    target_url: str
    quantity: int
    status: str
    created_at: Any | None = None


class ServiceResponse(BaseModel):
    id: int
    name: str
    type: str
    price_per_hundred: float
    description: str | None = None
