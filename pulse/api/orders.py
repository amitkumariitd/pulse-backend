"""Order management endpoints for Pulse internal API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import secrets
import asyncpg
from fastapi import APIRouter, Request, Depends, HTTPException, status
from shared.models.orders import InternalCreateOrderRequest, OrderResponse, ErrorResponse
from shared.observability.logger import get_logger
from shared.observability.context import RequestContext
from pulse.repositories.order_repository import OrderRepository

logger = get_logger("pulse.api.orders")
router = APIRouter()


def get_db_pool():
    """Dependency to get database pool.

    Import here to avoid circular dependency.
    """
    from pulse.main import get_db_pool as _get_db_pool
    return _get_db_pool()


def generate_order_id() -> str:
    """Generate unique ID for order.
    
    Format: ord + Unix timestamp (seconds) + 12 hexadecimal characters
    Example: ord1735228800a1b2c3d4e5f6
    """
    timestamp = int(time.time())
    random_hex = secrets.token_hex(6)
    return f"ord{timestamp}{random_hex}"


@router.post("/internal/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: Request,
    order_data: InternalCreateOrderRequest,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Create a new order in the database.
    
    This endpoint is called by GAPI after validation.
    Assumes all inputs are already validated.
    """
    ctx: RequestContext = request.state.context
    order_repo = OrderRepository(pool)
    
    # Generate order ID
    order_id = generate_order_id()
    
    logger.info("Creating order", ctx, data={
        "order_id": order_id,
        "instrument": order_data.instrument,
        "side": order_data.side,
        "total_quantity": order_data.total_quantity,
        "num_splits": order_data.num_splits
    })
    
    try:
        # Create order in database
        created_order = await order_repo.create_order(
            order_id=order_id,
            instrument=order_data.instrument,
            side=order_data.side,
            total_quantity=order_data.total_quantity,
            num_splits=order_data.num_splits,
            duration_minutes=order_data.duration_minutes,
            randomize=order_data.randomize,
            order_unique_key=order_data.order_unique_key,
            ctx=ctx
        )
        
        logger.info("Order created successfully", ctx, data={"order_id": order_id})
        
        # Return minimal response
        return OrderResponse(
            order_id=created_order['id'],
            order_unique_key=created_order['order_unique_key']
        )
        
    except asyncpg.UniqueViolationError:
        # Duplicate order_unique_key
        logger.warning("Duplicate order_unique_key", ctx, data={
            "order_unique_key": order_data.order_unique_key
        })
        
        # Try to find existing order
        try:
            existing_order = await order_repo.get_order_by_unique_key(order_data.order_unique_key, ctx)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "DUPLICATE_ORDER_UNIQUE_KEY",
                        "message": "Order unique key already exists",
                        "details": {
                            "order_unique_key": order_data.order_unique_key,
                            "existing_order_id": existing_order['id'] if existing_order else None
                        }
                    }
                }
            )
        except Exception:
            # If we can't find the existing order, still return 409
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "DUPLICATE_ORDER_UNIQUE_KEY",
                        "message": "Order unique key already exists",
                        "details": {
                            "order_unique_key": order_data.order_unique_key
                        }
                    }
                }
            )
    
    except asyncpg.PostgresError as e:
        logger.error("Database error creating order", ctx, data={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to create order",
                    "details": {}
                }
            }
        )
    
    except Exception as e:
        logger.error("Unexpected error creating order", ctx, data={"error": str(e)})
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

