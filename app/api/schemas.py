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

    user_id: int
    service_id: int
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
