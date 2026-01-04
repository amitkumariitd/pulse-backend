"""Order management endpoints for GAPI public API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from fastapi import APIRouter, Request, HTTPException, status, Header
from typing import Optional
from pydantic import ValidationError
from gapi.models.orders import CreateOrderRequest, InternalCreateOrderRequest, OrderResponse
from shared.observability.logger import get_logger
from shared.observability.context import RequestContext
from gapi.clients.pulse_client import PulseClient

logger = get_logger("gapi.api.orders")
router = APIRouter()


def validate_auth_token(authorization: Optional[str]) -> None:
    """Validate Bearer token.
    
    Args:
        authorization: Authorization header value
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Missing or invalid authentication token",
                    "details": {}
                }
            }
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Missing or invalid authentication token",
                    "details": {}
                }
            }
        )
    
    # TODO: Implement actual JWT validation
    # For now, just check that token exists
    token = authorization[7:]  # Remove "Bearer " prefix
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Missing or invalid authentication token",
                    "details": {}
                }
            }
        )


@router.post("/api/orders", response_model=OrderResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_order(
    request: Request,
    order_data: CreateOrderRequest,
    authorization: Optional[str] = Header(None)
):
    """Place an order that supports splitting into multiple slices.
    
    This endpoint validates the request and forwards it to Pulse service.
    """
    ctx: RequestContext = request.state.context
    
    # Validate authentication
    validate_auth_token(authorization)
    
    logger.info("Received order creation request", ctx, data={
        "instrument": order_data.instrument,
        "side": order_data.side,
        "total_quantity": order_data.total_quantity,
        "num_splits": order_data.split_config.num_splits
    })
    
    # Validate total_quantity >= num_splits
    if order_data.total_quantity < order_data.split_config.num_splits:
        logger.warning("Invalid quantity vs splits", ctx, data={
            "total_quantity": order_data.total_quantity,
            "num_splits": order_data.split_config.num_splits
        })
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_QUANTITY",
                    "message": "Total quantity must be >= num_splits",
                    "details": {
                        "total_quantity": order_data.total_quantity,
                        "num_splits": order_data.split_config.num_splits
                    }
                }
            }
        )
    
    # Convert to internal request format
    internal_request = InternalCreateOrderRequest(
        order_unique_key=order_data.order_unique_key,
        instrument=order_data.instrument,
        side=order_data.side,
        total_quantity=order_data.total_quantity,
        split_config=order_data.split_config
    )
    
    # Call Pulse service
    pulse_client = PulseClient()
    
    try:
        response = await pulse_client.create_order(internal_request, ctx)
        
        logger.info("Order created successfully", ctx, data={
            "order_id": response.order_id
        })

        # Return minimal response per GAPI contract
        return OrderResponse(
            order_id=response.order_id,
            order_unique_key=order_data.order_unique_key
        )
        
    except httpx.HTTPStatusError as e:
        # Forward Pulse errors to client
        if e.response.status_code == status.HTTP_409_CONFLICT:
            logger.warning("Duplicate order unique key", ctx)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=e.response.json()
            )
        else:
            logger.error("Pulse service error", ctx, data={
                "status_code": e.response.status_code
            })
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {}
                    }
                }
            )
    
    except httpx.RequestError as e:
        logger.error("Failed to connect to Pulse", ctx, data={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {}
                }
            }
        )

    except Exception as e:
        logger.error("Unexpected error in create_order", ctx, data={
            "error_type": type(e).__name__,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {}
                }
            }
        )

