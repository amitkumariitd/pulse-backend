"""Repository for order slice operations."""
import asyncpg
from typing import Optional
from datetime import datetime
from shared.database.base_repository import BaseRepository
from shared.observability.context import RequestContext, generate_request_id
from shared.observability.logger import get_logger

logger = get_logger("pulse.repositories.order_slice")


class OrderSliceRepository(BaseRepository):
    """Repository for order slice operations.
    
    Handles CRUD operations for the order_slices table (child orders).
    """
    
    async def create_order_slice(
        self,
        slice_id: str,
        order_id: str,
        instrument: str,
        side: str,
        quantity: int,
        sequence_number: int,
        scheduled_at: datetime,
        ctx: RequestContext
    ) -> dict:
        """Create a new order slice.
        
        Args:
            slice_id: Unique slice identifier
            order_id: Parent order ID
            instrument: Trading symbol (inherited from parent)
            side: Order side (inherited from parent)
            quantity: Shares for this slice
            sequence_number: Order in the split sequence (1, 2, 3...)
            scheduled_at: When this slice should execute
            ctx: Request context with tracing information
            
        Returns:
            Created order slice record as dict
            
        Raises:
            asyncpg.UniqueViolationError: If (order_id, sequence_number) already exists
            asyncpg.PostgresError: For other database errors
        """
        conn = await self.get_connection()
        try:
            # Generate new request_id for async workers
            async_request_id = generate_request_id()

            result = await conn.fetchrow(
                """
                INSERT INTO order_slices (
                    id, order_id, instrument, side, quantity,
                    sequence_number, status, scheduled_at,
                    origin_trace_id, origin_trace_source, origin_request_id, origin_request_source, request_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING *
                """,
                slice_id,
                order_id,
                instrument,
                side,
                quantity,
                sequence_number,
                'PENDING',  # Initial status
                scheduled_at,
                ctx.trace_id,           # Origin trace ID
                ctx.trace_source,       # Origin trace source
                ctx.request_id,         # Origin request ID
                ctx.request_source,     # Origin request source
                async_request_id        # New request_id for async workers
            )
            
            logger.info("Order slice created", ctx, data={
                "slice_id": slice_id,
                "order_id": order_id,
                "sequence_number": sequence_number
            })
            return dict(result)
        except asyncpg.UniqueViolationError:
            logger.warning("Duplicate order slice sequence", ctx, data={
                "order_id": order_id,
                "sequence_number": sequence_number
            })
            raise
        except asyncpg.PostgresError as e:
            logger.error("Failed to create order slice", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)
    
    async def create_order_slices_batch(
        self,
        slices: list[dict],
        ctx: RequestContext
    ) -> int:
        """Create multiple order slices in a single transaction.
        
        Args:
            slices: List of slice data dicts, each containing:
                - id, order_id, instrument, side, quantity,
                  sequence_number, scheduled_at
            ctx: Request context
            
        Returns:
            Number of slices created
        """
        conn = await self.get_connection()
        try:
            # Use a transaction for batch insert
            async with conn.transaction():
                count = 0
                for slice_data in slices:
                    # Generate new request_id for each slice
                    async_request_id = generate_request_id()

                    await conn.execute(
                        """
                        INSERT INTO order_slices (
                            id, order_id, instrument, side, quantity,
                            sequence_number, status, scheduled_at,
                            origin_trace_id, origin_trace_source, origin_request_id, origin_request_source, request_id
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        """,
                        slice_data['id'],
                        slice_data['order_id'],
                        slice_data['instrument'],
                        slice_data['side'],
                        slice_data['quantity'],
                        slice_data['sequence_number'],
                        'PENDING',
                        slice_data['scheduled_at'],
                        ctx.trace_id,           # Origin trace ID
                        ctx.trace_source,       # Origin trace source
                        ctx.request_id,         # Origin request ID
                        ctx.request_source,     # Origin request source
                        async_request_id        # New request_id for async workers
                    )
                    count += 1
            
            logger.info("Order slices created in batch", ctx, data={
                "count": count,
                "order_id": slices[0]['order_id'] if slices else None
            })
            return count
        except asyncpg.PostgresError as e:
            logger.error("Failed to create order slices batch", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)

    async def get_slices_by_order_id(
        self,
        order_id: str,
        ctx: RequestContext
    ) -> list[dict]:
        """Get all slices for a parent order.

        Args:
            order_id: Parent order ID
            ctx: Request context

        Returns:
            List of order slice records, ordered by sequence_number
        """
        conn = await self.get_connection()
        try:
            results = await conn.fetch(
                """
                SELECT * FROM order_slices
                WHERE order_id = $1
                ORDER BY sequence_number ASC
                """,
                order_id
            )

            slices = [dict(row) for row in results]
            logger.info("Retrieved order slices", ctx, data={
                "order_id": order_id,
                "count": len(slices)
            })
            return slices
        except asyncpg.PostgresError as e:
            logger.error("Failed to get order slices", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)

    async def get_slice_by_id(
        self,
        slice_id: str,
        ctx: RequestContext
    ) -> Optional[dict]:
        """Get order slice by ID.

        Args:
            slice_id: Slice ID to retrieve
            ctx: Request context

        Returns:
            Order slice record as dict, or None if not found
        """
        conn = await self.get_connection()
        try:
            result = await conn.fetchrow(
                "SELECT * FROM order_slices WHERE id = $1",
                slice_id
            )

            if result:
                logger.info("Order slice retrieved", ctx, data={"slice_id": slice_id})
                return dict(result)
            else:
                logger.warning("Order slice not found", ctx, data={"slice_id": slice_id})
                return None
        except asyncpg.PostgresError as e:
            logger.error("Failed to get order slice", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)

    async def update_slice_status(
        self,
        slice_id: str,
        new_status: str,
        ctx: RequestContext
    ) -> bool:
        """Update order slice status.

        Args:
            slice_id: Slice ID to update
            new_status: New status (SCHEDULED, READY, IN_PROGRESS, PROCESSED, SKIPPED)
            ctx: Request context

        Returns:
            True if updated, False if slice not found
        """
        conn = await self.get_connection()
        try:
            result = await conn.execute(
                """
                UPDATE order_slices
                SET status = $1
                WHERE id = $2
                """,
                new_status,
                slice_id
            )

            updated = result == "UPDATE 1"
            if updated:
                logger.info("Order slice status updated", ctx, data={
                    "slice_id": slice_id,
                    "new_status": new_status
                })
            else:
                logger.warning("Order slice not found for status update", ctx, data={
                    "slice_id": slice_id
                })

            return updated
        except asyncpg.PostgresError as e:
            logger.error("Failed to update order slice status", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)

