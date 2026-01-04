"""Repository for order operations."""
import asyncpg
from typing import Optional
from shared.database.base_repository import BaseRepository
from shared.observability.context import RequestContext
from shared.observability.logger import get_logger

logger = get_logger("pulse.repositories.order")


class OrderRepository(BaseRepository):
    """Repository for parent order operations.
    
    Handles CRUD operations for the orders table (parent orders).
    """
    
    async def create_order(
        self,
        order_id: str,
        instrument: str,
        side: str,
        total_quantity: int,
        num_splits: int,
        duration_minutes: int,
        randomize: bool,
        order_unique_key: str,
        ctx: RequestContext
    ) -> dict:
        """Create a new parent order.
        
        Args:
            order_id: Unique order identifier
            instrument: Trading symbol (e.g., "NSE:RELIANCE")
            side: Order side ("BUY" or "SELL")
            total_quantity: Total shares to trade
            num_splits: Number of child orders to create
            duration_minutes: Total duration in minutes
            randomize: Whether to apply randomization
            order_unique_key: Unique key for deduplication
            ctx: Request context with tracing information
            
        Returns:
            Created order record as dict
            
        Raises:
            asyncpg.UniqueViolationError: If order_unique_key already exists
            asyncpg.PostgresError: For other database errors
        """
        conn = await self.get_connection()
        try:
            result = await conn.fetchrow(
                """
                INSERT INTO orders (
                    id, instrument, side, total_quantity, num_splits,
                    duration_minutes, randomize, order_unique_key,
                    order_queue_status,
                    trace_id, request_id, trace_source
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING *
                """,
                order_id,
                instrument,
                side,
                total_quantity,
                num_splits,
                duration_minutes,
                randomize,
                order_unique_key,
                'PENDING',  # Initial status
                ctx.trace_id,
                ctx.request_id,
                ctx.trace_source
            )
            
            logger.info("Order created", ctx, data={"order_id": order_id})
            return dict(result)
        except asyncpg.UniqueViolationError:
            logger.warning("Duplicate order_unique_key", ctx, data={
                "order_unique_key": order_unique_key
            })
            raise
        except asyncpg.PostgresError as e:
            logger.error("Failed to create order", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)
    
    async def get_order_by_id(self, order_id: str, ctx: RequestContext) -> Optional[dict]:
        """Get order by ID.
        
        Args:
            order_id: Order ID to retrieve
            ctx: Request context
            
        Returns:
            Order record as dict, or None if not found
        """
        conn = await self.get_connection()
        try:
            result = await conn.fetchrow(
                "SELECT * FROM orders WHERE id = $1",
                order_id
            )
            
            if result:
                logger.info("Order retrieved", ctx, data={"order_id": order_id})
                return dict(result)
            else:
                logger.warning("Order not found", ctx, data={"order_id": order_id})
                return None
        except asyncpg.PostgresError as e:
            logger.error("Failed to get order", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)
    
    async def get_order_by_unique_key(
        self,
        order_unique_key: str,
        ctx: RequestContext
    ) -> Optional[dict]:
        """Get order by unique key (for deduplication).
        
        Args:
            order_unique_key: Unique key to search for
            ctx: Request context
            
        Returns:
            Order record as dict, or None if not found
        """
        conn = await self.get_connection()
        try:
            result = await conn.fetchrow(
                "SELECT * FROM orders WHERE order_unique_key = $1",
                order_unique_key
            )
            
            if result:
                logger.info("Order found by unique key", ctx, data={
                    "order_unique_key": order_unique_key,
                    "order_id": result['id']
                })
                return dict(result)
            else:
                return None
        except asyncpg.PostgresError as e:
            logger.error("Failed to get order by unique key", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)

    async def update_order_status(
        self,
        order_id: str,
        new_status: str,
        ctx: RequestContext,
        skip_reason: Optional[str] = None
    ) -> bool:
        """Update order queue status.

        Args:
            order_id: Order ID to update
            new_status: New status (PENDING, IN_PROGRESS, DONE, SKIPPED)
            ctx: Request context
            skip_reason: Reason for skipping (required if status is SKIPPED)

        Returns:
            True if updated, False if order not found
        """
        conn = await self.get_connection()
        try:
            result = await conn.execute(
                """
                UPDATE orders
                SET order_queue_status = $1,
                    order_queue_skip_reason = $2
                WHERE id = $3
                """,
                new_status,
                skip_reason,
                order_id
            )

            updated = result == "UPDATE 1"
            if updated:
                logger.info("Order status updated", ctx, data={
                    "order_id": order_id,
                    "new_status": new_status
                })
            else:
                logger.warning("Order not found for status update", ctx, data={
                    "order_id": order_id
                })

            return updated
        except asyncpg.PostgresError as e:
            logger.error("Failed to update order status", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)

    async def mark_split_complete(
        self,
        order_id: str,
        total_child_orders: int,
        ctx: RequestContext
    ) -> bool:
        """Mark order splitting as complete.

        Args:
            order_id: Order ID to update
            total_child_orders: Number of child orders created
            ctx: Request context

        Returns:
            True if updated, False if order not found
        """
        conn = await self.get_connection()
        try:
            result = await conn.execute(
                """
                UPDATE orders
                SET order_queue_status = 'COMPLETED',
                    split_completed_at = NOW()
                WHERE id = $1
                """,
                order_id
            )

            updated = result == "UPDATE 1"
            if updated:
                logger.info("Order marked as split complete", ctx, data={
                    "order_id": order_id,
                    "total_child_orders": total_child_orders
                })
            else:
                logger.warning("Order not found for split complete", ctx, data={
                    "order_id": order_id
                })

            return updated
        except asyncpg.PostgresError as e:
            logger.error("Failed to mark split complete", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)

    async def get_pending_orders(
        self,
        limit: int,
        ctx: RequestContext
    ) -> list[dict]:
        """Get pending orders for splitting (with locking).

        Uses SELECT FOR UPDATE SKIP LOCKED for concurrency safety.

        Args:
            limit: Maximum number of orders to retrieve
            ctx: Request context

        Returns:
            List of order records
        """
        conn = await self.get_connection()
        try:
            results = await conn.fetch(
                """
                SELECT * FROM orders
                WHERE order_queue_status = 'PENDING'
                ORDER BY created_at ASC
                LIMIT $1
                FOR UPDATE SKIP LOCKED
                """,
                limit
            )

            orders = [dict(row) for row in results]
            logger.info("Retrieved pending orders", ctx, data={
                "count": len(orders)
            })
            return orders
        except asyncpg.PostgresError as e:
            logger.error("Failed to get pending orders", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)

