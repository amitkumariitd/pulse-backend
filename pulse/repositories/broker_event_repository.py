"""Repository for broker event operations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncpg
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from shared.database.base_repository import BaseRepository
from shared.observability.context import RequestContext
from shared.observability.logger import get_logger

logger = get_logger("pulse.repositories.broker_event")


class BrokerEventRepository(BaseRepository):
    """Repository for broker event operations.
    
    Handles CRUD operations for the order_slice_broker_events table.
    """
    
    async def create_broker_event(
        self,
        event_id: str,
        execution_id: str,
        slice_id: str,
        event_sequence: int,
        event_type: str,
        attempt_number: int,
        attempt_id: str,
        executor_id: str,
        broker_name: str,
        is_success: bool,
        broker_order_id: Optional[str] = None,
        request_method: Optional[str] = None,
        request_endpoint: Optional[str] = None,
        request_payload: Optional[Dict[str, Any]] = None,
        response_status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[int] = None,
        broker_status: Optional[str] = None,
        broker_message: Optional[str] = None,
        filled_quantity: Optional[int] = None,
        pending_quantity: Optional[int] = None,
        average_price: Optional[Decimal] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        ctx: RequestContext = None
    ) -> dict:
        """Create a new broker event record.
        
        Args:
            event_id: Unique event identifier
            execution_id: Execution ID this event belongs to
            slice_id: Order slice ID
            event_sequence: Sequence number for this execution
            event_type: Type of event (PLACE_ORDER, STATUS_POLL, CANCEL_REQUEST)
            attempt_number: Attempt number within this execution
            attempt_id: Unique attempt identifier
            executor_id: Worker ID
            broker_name: Broker name (e.g., 'zerodha')
            is_success: Whether the broker call succeeded
            broker_order_id: Broker order ID (if available)
            request_method: HTTP method
            request_endpoint: API endpoint
            request_payload: Request payload
            response_status_code: HTTP status code
            response_body: Response body
            response_time_ms: Response time in milliseconds
            broker_status: Parsed broker status
            broker_message: Broker message
            filled_quantity: Filled quantity
            pending_quantity: Pending quantity
            average_price: Average price
            error_code: Error code (if failed)
            error_message: Error message (if failed)
            ctx: Request context
            
        Returns:
            Created broker event record as dict
        """
        conn = await self.get_connection()
        try:
            now = datetime.utcnow()
            
            result = await conn.fetchrow(
                """
                INSERT INTO order_slice_broker_events (
                    id, execution_id, slice_id, event_sequence, event_type,
                    attempt_number, attempt_id, executor_id, broker_name,
                    broker_order_id, request_method, request_endpoint, request_payload,
                    response_status_code, response_body, response_time_ms,
                    broker_status, broker_message, filled_quantity, pending_quantity,
                    average_price, is_success, error_code, error_message,
                    event_timestamp, request_id, created_at, updated_at
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                    $21, $22, $23, $24, $25, $26, $27, $28
                )
                RETURNING *
                """,
                event_id,
                execution_id,
                slice_id,
                event_sequence,
                event_type,
                attempt_number,
                attempt_id,
                executor_id,
                broker_name,
                broker_order_id,
                request_method,
                request_endpoint,
                request_payload,
                response_status_code,
                response_body,
                response_time_ms,
                broker_status,
                broker_message,
                filled_quantity,
                pending_quantity,
                average_price,
                is_success,
                error_code,
                error_message,
                now,
                ctx.request_id if ctx else None,
                now,
                now
            )
            
            if ctx:
                logger.info("Broker event created", ctx, data={
                    "event_id": event_id,
                    "execution_id": execution_id,
                    "event_type": event_type,
                    "is_success": is_success,
                    "broker_order_id": broker_order_id
                })
            
            return dict(result)
            
        finally:
            await self.release_connection(conn)

