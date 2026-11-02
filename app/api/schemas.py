from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProxyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ip: str = Field(..., min_length=7, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    username: Optional[str] = None
    password: Optional[str] = None


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[int] = None
    service_id: int
    platform: str = Field(default="test", pattern="^(facebook|instagram|tiktok|discord|x|test)$")
    action_type: str = Field(default="navigate", min_length=1, max_length=64)
    target_url: HttpUrl
    quantity: int = Field(default=1, ge=1, le=10000)
    proxy: Optional[ProxyConfig] = None


class OrderResponse(BaseModel):
    id: int
    user_id: int
    service_id: int
    target_url: str
    quantity: int
    status: str
    created_at: Optional[datetime] = None


class AuthCredentials(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class ServiceResponse(BaseModel):
    id: int
    name: str
    type: str
    price_per_hundred: float
    description: Optional[str] = None
