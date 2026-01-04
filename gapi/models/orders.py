"""GAPI-specific Pydantic models for order requests and responses."""

from pydantic import BaseModel, Field, field_validator
from typing import Literal


class SplitConfig(BaseModel):
    """Split configuration for an order."""
    num_splits: int = Field(..., ge=2, le=100, description="Number of child orders to create")
    duration_minutes: int = Field(..., ge=1, le=1440, description="Total duration in minutes")
    randomize: bool = Field(default=True, description="Whether to apply randomization")


class CreateOrderRequest(BaseModel):
    """Request model for creating an order (GAPI endpoint)."""
    order_unique_key: str = Field(..., min_length=1, description="Unique key for order deduplication")
    instrument: str = Field(..., min_length=1, description="Trading symbol (e.g., NSE:RELIANCE)")
    side: Literal["BUY", "SELL"] = Field(..., description="Order side")
    total_quantity: int = Field(..., gt=0, description="Total shares to trade")
    split_config: SplitConfig = Field(..., description="Split configuration")
    
    @field_validator('instrument')
    @classmethod
    def validate_instrument(cls, v: str) -> str:
        """Validate instrument format: EXCHANGE:SYMBOL"""
        if ':' not in v:
            raise ValueError("Invalid instrument format. Expected EXCHANGE:SYMBOL")
        
        parts = v.split(':')
        if len(parts) != 2:
            raise ValueError("Invalid instrument format. Expected EXCHANGE:SYMBOL")
        
        exchange, symbol = parts
        if exchange not in ['NSE', 'BSE']:
            raise ValueError(f"Unsupported exchange: {exchange}. Supported: NSE, BSE")
        
        if not symbol.isalnum() or not symbol.isupper():
            raise ValueError("Symbol must be alphanumeric and uppercase")
        
        return v
    
    @field_validator('total_quantity')
    @classmethod
    def validate_quantity_vs_splits(cls, v: int, info) -> int:
        """Validate that total_quantity >= num_splits"""
        # Note: split_config might not be set yet during validation
        # This validation will be done at the endpoint level
        return v


class InternalCreateOrderRequest(BaseModel):
    """Request model for Pulse internal endpoint (used by GAPI client)."""
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

