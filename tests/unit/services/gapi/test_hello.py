"""Unit tests for hello endpoint"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from gapi.main import hello


def test_hello_returns_message():
    """Test hello endpoint returns correct message"""
    # Arrange
    # (no setup needed)
    
    # Act
    result = hello()
    
    # Assert
    assert "message" in result
    assert result["message"] == "Hello from GAPI"


@patch('gapi.main.logger')
def test_hello_logs_with_data(mock_logger):
    """Test hello endpoint logs with endpoint data and auto-injected context"""
    # Act
    result = hello()

    # Assert
    mock_logger.info.assert_called_once()

    # Verify logger was called with data parameter
    call_args = mock_logger.info.call_args
    assert call_args[0][0] == "Hello endpoint called"
    assert call_args[1]['data'] == {"endpoint": "/api/hello"}

    assert result["message"] == "Hello from GAPI"

