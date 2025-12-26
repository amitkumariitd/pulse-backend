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


@patch('services.order_service.main.logger')
def test_health_logs_request(mock_logger):
    """Test health endpoint logs the request with auto-injected context"""
    # Act
    result = health()

    # Assert
    mock_logger.info.assert_called_once_with("Health check")
    assert result["status"] == "ok"

