"""HTTP client for calling Pulse service."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from shared.http.client import ContextPropagatingClient
from shared.observability.context import RequestContext
from shared.observability.logger import get_logger
from shared.models.orders import InternalCreateOrderRequest, OrderResponse
from config.settings import get_settings

logger = get_logger("gapi.clients.pulse")


class PulseClient:
    """Client for calling Pulse internal API."""
    
    def __init__(self, base_url: str | None = None):
        """Initialize Pulse client.
        
        Args:
            base_url: Base URL for Pulse service. If None, uses settings.
        """
        if base_url is None:
            settings = get_settings()
            base_url = settings.pulse_api_base_url or "http://localhost:8001"
        
        self.base_url = base_url
        self.client = None
    
    def _get_client(self, ctx: RequestContext) -> ContextPropagatingClient:
        """Get or create HTTP client with context propagation.
        
        Args:
            ctx: Request context to propagate
            
        Returns:
            ContextPropagatingClient instance
        """
        return ContextPropagatingClient(self.base_url, ctx)
    
    async def create_order(
        self,
        order_data: InternalCreateOrderRequest,
        ctx: RequestContext
    ) -> OrderResponse:
        """Create order in Pulse service.
        
        Args:
            order_data: Order creation request
            ctx: Request context
            
        Returns:
            OrderResponse from Pulse
            
        Raises:
            httpx.HTTPStatusError: If Pulse returns an error
            httpx.RequestError: If request fails
        """
        client = self._get_client(ctx)
        
        logger.info("Calling Pulse to create order", ctx, data={
            "instrument": order_data.instrument,
            "side": order_data.side,
            "total_quantity": order_data.total_quantity
        })
        
        try:
            response = await client.post(
                "/internal/orders",
                json=order_data.model_dump()
            )
            response.raise_for_status()
            
            logger.info("Order created in Pulse", ctx, data={
                "status_code": response.status_code
            })
            
            return OrderResponse(**response.json())
            
        except httpx.HTTPStatusError as e:
            logger.error("Pulse returned error", ctx, data={
                "status_code": e.response.status_code,
                "response": e.response.text
            })
            raise
        
        except httpx.RequestError as e:
            logger.error("Failed to call Pulse", ctx, data={
                "error": str(e)
            })
            raise
        
        finally:
            await client.close()

