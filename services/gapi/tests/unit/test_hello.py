"""Unit tests for hello endpoint"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from services.gapi.main import hello


def test_hello_returns_message():
    """Test hello endpoint returns correct message"""
    # Arrange
    # (no setup needed)
    
    # Act
    result = hello()
    
    # Assert
    assert "message" in result
    assert result["message"] == "Hello from GAPI"


@patch('services.gapi.main.get_trace_context')
@patch('services.gapi.main.logger')
def test_hello_logs_with_data(mock_logger, mock_get_context):
    """Test hello endpoint logs with endpoint data"""
    # Arrange
    mock_get_context.return_value = {
        'trace_id': 't-abc',
        'request_id': 'r-xyz'
    }
    
    # Act
    result = hello()
    
    # Assert
    mock_get_context.assert_called_once()
    mock_logger.info.assert_called_once()
    
    # Verify logger was called with data parameter
    call_args = mock_logger.info.call_args
    assert call_args[1]['data'] == {"endpoint": "/api/hello"}
    
    assert result["message"] == "Hello from GAPI"

