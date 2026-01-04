"""Unit tests for Pulse orders API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg
from fastapi import Request
from shared.observability.context import RequestContext
from pulse.api.orders import create_order, generate_order_id
from pulse.models.orders import InternalCreateOrderRequest, SplitConfig


def test_generate_order_id_format():
    """Test that order IDs have the correct format."""
    order_id = generate_order_id()
    
    assert order_id.startswith('ord')
    assert len(order_id) == 25  # 'ord' + 10 digits + 12 hex chars
    
    # Verify timestamp part is numeric
    timestamp_part = order_id[3:13]
    assert timestamp_part.isdigit()
    
    # Verify random part is hexadecimal
    random_part = order_id[13:]
    assert len(random_part) == 12
    assert all(c in '0123456789abcdef' for c in random_part)


def test_generate_order_id_uniqueness():
    """Test that consecutive order IDs are unique."""
    id1 = generate_order_id()
    id2 = generate_order_id()
    
    assert id1 != id2


@pytest.mark.asyncio
async def test_create_order_success():
    """Test successful order creation."""
    # Arrange
    mock_pool = MagicMock()
    mock_repo = AsyncMock()
    mock_repo.create_order.return_value = {
        'id': 'ord1234567890abcdef',
        'order_unique_key': 'ouk_test123'
    }
    
    request = MagicMock(spec=Request)
    request.state.context = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_id="s12345678",
        span_source="TEST"
    )
    
    order_data = InternalCreateOrderRequest(
        order_unique_key="ouk_test123",
        instrument="NSE:RELIANCE",
        side="BUY",
        total_quantity=100,
        split_config=SplitConfig(
            num_splits=5,
            duration_minutes=60,
            randomize=True
        )
    )
    
    # Act
    with patch('pulse.api.orders.OrderRepository', return_value=mock_repo):
        response = await create_order(request, order_data, mock_pool)
    
    # Assert
    assert response.order_id == 'ord1234567890abcdef'
    assert response.order_unique_key == 'ouk_test123'

    # Verify repository was called
    mock_repo.create_order.assert_called_once()


@pytest.mark.asyncio
async def test_create_order_duplicate_key():
    """Test order creation with duplicate unique key."""
    # Arrange
    mock_pool = MagicMock()
    mock_repo = AsyncMock()
    mock_repo.create_order.side_effect = asyncpg.UniqueViolationError("duplicate key")
    mock_repo.get_order_by_unique_key.return_value = {
        'id': 'ord_existing123',
        'order_unique_key': 'ouk_test123'
    }
    
    request = MagicMock(spec=Request)
    request.state.context = RequestContext(
        trace_id="t1234567890abcdef1234",
        trace_source="TEST",
        request_id="r1234567890abcdef1234",
        request_source="TEST",
        span_id="s12345678",
        span_source="TEST"
    )
    
    order_data = InternalCreateOrderRequest(
        order_unique_key="ouk_test123",
        instrument="NSE:RELIANCE",
        side="BUY",
        total_quantity=100,
        split_config=SplitConfig(
            num_splits=5,
            duration_minutes=60,
            randomize=True
        )
    )

    # Act & Assert
    with patch('pulse.api.orders.OrderRepository', return_value=mock_repo):
        with pytest.raises(Exception) as exc_info:
            await create_order(request, order_data, mock_pool)

        # Should raise HTTPException with 409 status
        assert exc_info.value.status_code == 409
        assert "DUPLICATE_ORDER_UNIQUE_KEY" in str(exc_info.value.detail)

