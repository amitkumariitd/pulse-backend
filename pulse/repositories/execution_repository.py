"""Repository for order slice execution operations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncpg
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from shared.database.base_repository import BaseRepository
from shared.observability.context import RequestContext
from shared.observability.logger import get_logger

logger = get_logger("pulse.repositories.execution")


class ExecutionRepository(BaseRepository):
    """Repository for order slice execution operations.
    
    Handles CRUD operations for the order_slice_executions table.
    """
    
    async def create_execution(
        self,
        execution_id: str,
        slice_id: str,
        attempt_id: str,
        executor_id: str,
        timeout_minutes: int,
        ctx: RequestContext
    ) -> dict:
        """Create a new execution record (claim ownership of a slice).
        
        Args:
            execution_id: Unique execution identifier
            slice_id: Order slice ID being executed
            attempt_id: Unique attempt identifier
            executor_id: Worker ID claiming this execution
            timeout_minutes: Minutes until ownership expires
            ctx: Request context with tracing information
            
        Returns:
            Created execution record as dict
            
        Raises:
            asyncpg.UniqueViolationError: If slice_id already has an execution
            asyncpg.PostgresError: For other database errors
        """
        conn = await self.get_connection()
        try:
            now = datetime.utcnow()
            timeout_at = now + timedelta(minutes=timeout_minutes)
            
            result = await conn.fetchrow(
                """
                INSERT INTO order_slice_executions (
                    id, slice_id, attempt_id, executor_id,
                    executor_claimed_at, executor_timeout_at, last_heartbeat_at,
                    execution_status, placement_attempts,
                    request_id, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING *
                """,
                execution_id,
                slice_id,
                attempt_id,
                executor_id,
                now,
                timeout_at,
                now,
                'CLAIMED',
                0,
                ctx.request_id,
                now,
                now
            )
            
            logger.info("Execution record created", ctx, data={
                "execution_id": execution_id,
                "slice_id": slice_id,
                "attempt_id": attempt_id,
                "executor_id": executor_id,
                "timeout_at": timeout_at.isoformat()
            })
            
            return dict(result)
            
        finally:
            await self.release_connection(conn)
    
    async def update_execution_status(
        self,
        execution_id: str,
        execution_status: str,
        broker_order_id: Optional[str] = None,
        broker_order_status: Optional[str] = None,
        filled_quantity: Optional[int] = None,
        average_price: Optional[Decimal] = None,
        execution_result: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        ctx: RequestContext = None
    ) -> dict:
        """Update execution status and details.
        
        Args:
            execution_id: Execution ID to update
            execution_status: New execution status
            broker_order_id: Broker order ID (if available)
            broker_order_status: Broker order status (if available)
            filled_quantity: Filled quantity (if available)
            average_price: Average fill price (if available)
            execution_result: Execution result (if terminal)
            error_code: Error code (if failed)
            error_message: Error message (if failed)
            ctx: Request context
            
        Returns:
            Updated execution record as dict
        """
        conn = await self.get_connection()
        try:
            now = datetime.utcnow()
            
            # Build dynamic update query
            updates = ["execution_status = $2", "updated_at = $3"]
            params = [execution_id, execution_status, now]
            param_idx = 4
            
            if broker_order_id is not None:
                updates.append(f"broker_order_id = ${param_idx}")
                params.append(broker_order_id)
                param_idx += 1
            
            if broker_order_status is not None:
                updates.append(f"broker_order_status = ${param_idx}")
                params.append(broker_order_status)
                param_idx += 1
            
            if filled_quantity is not None:
                updates.append(f"filled_quantity = ${param_idx}")
                params.append(filled_quantity)
                param_idx += 1
            
            if average_price is not None:
                updates.append(f"average_price = ${param_idx}")
                params.append(average_price)
                param_idx += 1

            if execution_result is not None:
                updates.append(f"execution_result = ${param_idx}")
                params.append(execution_result)
                param_idx += 1

            if error_code is not None:
                updates.append(f"error_code = ${param_idx}")
                params.append(error_code)
                param_idx += 1

            if error_message is not None:
                updates.append(f"error_message = ${param_idx}")
                params.append(error_message)
                param_idx += 1

            # Mark as completed if terminal status
            if execution_status == 'COMPLETED':
                updates.append(f"completed_at = ${param_idx}")
                params.append(now)
                param_idx += 1

            query = f"""
                UPDATE order_slice_executions
                SET {', '.join(updates)}
                WHERE id = $1
                RETURNING *
            """

            result = await conn.fetchrow(query, *params)

            if ctx:
                logger.info("Execution status updated", ctx, data={
                    "execution_id": execution_id,
                    "execution_status": execution_status,
                    "broker_order_id": broker_order_id,
                    "execution_result": execution_result
                })

            return dict(result) if result else None

        finally:
            await self.release_connection(conn)

    async def update_heartbeat(
        self,
        execution_id: str,
        extend_timeout_minutes: int,
        ctx: RequestContext
    ) -> dict:
        """Update heartbeat and extend timeout.

        Args:
            execution_id: Execution ID to update
            extend_timeout_minutes: Minutes to extend timeout from now
            ctx: Request context

        Returns:
            Updated execution record as dict
        """
        conn = await self.get_connection()
        try:
            now = datetime.utcnow()
            new_timeout = now + timedelta(minutes=extend_timeout_minutes)

            result = await conn.fetchrow(
                """
                UPDATE order_slice_executions
                SET last_heartbeat_at = $2,
                    executor_timeout_at = $3,
                    updated_at = $4
                WHERE id = $1
                RETURNING *
                """,
                execution_id,
                now,
                new_timeout,
                now
            )

            return dict(result) if result else None

        finally:
            await self.release_connection(conn)

    async def get_execution_by_slice_id(
        self,
        slice_id: str,
        ctx: RequestContext
    ) -> Optional[dict]:
        """Get execution record by slice ID.

        Args:
            slice_id: Order slice ID
            ctx: Request context

        Returns:
            Execution record as dict, or None if not found
        """
        conn = await self.get_connection()
        try:
            result = await conn.fetchrow(
                """
                SELECT * FROM order_slice_executions
                WHERE slice_id = $1
                """,
                slice_id
            )

            return dict(result) if result else None

        finally:
            await self.release_connection(conn)

    async def find_timed_out_executions(
        self,
        ctx: RequestContext
    ) -> List[dict]:
        """Find executions that have timed out.

        Args:
            ctx: Request context

        Returns:
            List of timed-out execution records
        """
        conn = await self.get_connection()
        try:
            now = datetime.utcnow()

            results = await conn.fetch(
                """
                SELECT * FROM order_slice_executions
                WHERE execution_status IN ('CLAIMED', 'PLACED')
                  AND executor_timeout_at < $1
                ORDER BY executor_timeout_at ASC
                """,
                now
            )

            return [dict(r) for r in results]

        finally:
            await self.release_connection(conn)

