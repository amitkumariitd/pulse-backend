"""
Example: Repository implementation with PostgreSQL

This shows the complete repository pattern including:
- Connection management
- Tracing context propagation
- Parameterized queries
- Error handling
- History (handled automatically by triggers)
"""

import asyncpg
from typing import Optional
from pulse.shared.context import RequestContext
from pulse.shared.logging import get_logger

logger = get_logger(__name__)


class BaseRepository:
    """Base repository with connection pooling."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get connection from pool."""
        return await self.pool.acquire()
    
    async def release_connection(self, conn: asyncpg.Connection):
        """Release connection back to pool."""
        await self.pool.release(conn)


class OrderRepository(BaseRepository):
    """Repository for order operations."""
    
    async def create_order(self, order_data: dict, ctx: RequestContext) -> dict:
        """
        Create order - trigger automatically records in history.
        
        Args:
            order_data: Order data (id, instrument, quantity, side, order_type)
            ctx: Request context with tracing information
            
        Returns:
            Created order record
        """
        conn = await self.get_connection()
        try:
            result = await conn.fetchrow(
                """
                INSERT INTO orders (
                    id, instrument, quantity, side, order_type, status,
                    trace_id, request_id, tracing_source, request_source,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
                RETURNING *
                """,
                order_data['id'],
                order_data['instrument'],
                order_data['quantity'],
                order_data['side'],
                order_data['order_type'],
                'PENDING',
                ctx.trace_id,          # From RequestContext
                ctx.request_id,        # From RequestContext
                ctx.tracing_source,    # From RequestContext
                ctx.request_source     # From RequestContext
            )
            
            logger.info("Order created", ctx, data={"order_id": result['id']})
            return dict(result)
        except asyncpg.PostgresError as e:
            logger.error("Failed to create order", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)
    
    async def get_order(self, order_id: str, ctx: RequestContext) -> Optional[dict]:
        """Get order by ID."""
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
    
    async def update_order(self, order_id: str, updates: dict, ctx: RequestContext) -> dict:
        """
        Update order - trigger automatically records old state in history.
        
        Args:
            order_id: Order ID to update
            updates: Fields to update (e.g., {'status': 'FILLED'})
            ctx: Request context
            
        Returns:
            Updated order record
        """
        conn = await self.get_connection()
        try:
            result = await conn.fetchrow(
                """
                UPDATE orders 
                SET status = $1, updated_at = NOW()
                WHERE id = $2
                RETURNING *
                """,
                updates['status'],
                order_id
            )
            
            if result is None:
                raise ValueError(f"Order {order_id} not found")
            
            logger.info("Order updated", ctx, data={"order_id": order_id, "status": updates['status']})
            return dict(result)
        except asyncpg.PostgresError as e:
            logger.error("Failed to update order", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)
    
    async def delete_order(self, order_id: str, ctx: RequestContext) -> bool:
        """
        Delete order - trigger automatically records in history.
        
        Args:
            order_id: Order ID to delete
            ctx: Request context
            
        Returns:
            True if deleted, False if not found
        """
        conn = await self.get_connection()
        try:
            result = await conn.execute(
                "DELETE FROM orders WHERE id = $1",
                order_id
            )
            
            deleted = result == "DELETE 1"
            if deleted:
                logger.info("Order deleted", ctx, data={"order_id": order_id})
            else:
                logger.warning("Order not found for deletion", ctx, data={"order_id": order_id})
            
            return deleted
        except asyncpg.PostgresError as e:
            logger.error("Failed to delete order", ctx, data={"error": str(e)})
            raise
        finally:
            await self.release_connection(conn)

