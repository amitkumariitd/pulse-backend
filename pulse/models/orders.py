"""Pulse-specific Pydantic models for order requests and responses."""

from pydantic import BaseModel, Field
from typing import Literal


class SplitConfig(BaseModel):
    """Split configuration for an order."""
    num_splits: int = Field(..., ge=2, le=100, description="Number of child orders to create")
    duration_minutes: int = Field(..., ge=1, le=1440, description="Total duration in minutes")
    randomize: bool = Field(..., description="Whether to apply randomization")


class InternalCreateOrderRequest(BaseModel):
    """Request model for Pulse internal endpoint."""
    order_unique_key: str = Field(..., min_length=1)
    instrument: str = Field(..., min_length=1)
    side: Literal["BUY", "SELL"]
    total_quantity: int = Field(..., gt=0)
    split_config: SplitConfig = Field(..., description="Split configuration")


class OrderResponse(BaseModel):
    """Response model for order creation."""
    order_id: str
    order_unique_key: str


class ErrorDetail(BaseModel):
    """Error details model."""
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response model."""
    error: ErrorDetail

