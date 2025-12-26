"""Unit tests for health endpoint"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from services.order_service.main import health


def test_health_returns_ok():
    """Test health endpoint returns status ok"""
    # Arrange
    # (no setup needed)
    
    # Act
    result = health()
    
    # Assert
    assert result == {"status": "ok"}
    assert "status" in result
    assert result["status"] == "ok"


@patch('services.order_service.main.get_trace_context')
@patch('services.order_service.main.logger')
def test_health_logs_request(mock_logger, mock_get_context):
    """Test health endpoint logs the request"""
    # Arrange
    mock_get_context.return_value = {
        'trace_id': 't-123',
        'request_id': 'r-456'
    }
    
    # Act
    result = health()
    
    # Assert
    mock_get_context.assert_called_once()
    mock_logger.info.assert_called_once()
    assert result["status"] == "ok"

