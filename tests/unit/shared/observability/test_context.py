import re
import time
from shared.observability.context import (
    RequestContext,
    generate_trace_id,
    generate_request_id,
    generate_span_id,
    is_valid_trace_id,
    is_valid_request_id,
    is_valid_span_id,
    TRACE_ID_PATTERN,
    REQUEST_ID_PATTERN,
    SPAN_ID_PATTERN
)


def test_generate_trace_id_format():
    """Test that generated trace_id matches the expected format."""
    trace_id = generate_trace_id()
    
    assert trace_id.startswith('t')
    assert len(trace_id) == 23
    assert TRACE_ID_PATTERN.match(trace_id)


def test_generate_request_id_format():
    """Test that generated request_id matches the expected format."""
    request_id = generate_request_id()
    
    assert request_id.startswith('r')
    assert len(request_id) == 23
    assert REQUEST_ID_PATTERN.match(request_id)


def test_generate_trace_id_contains_timestamp():
    """Test that trace_id contains current timestamp."""
    before = int(time.time())
    trace_id = generate_trace_id()
    after = int(time.time())
    
    timestamp_str = trace_id[1:11]
    timestamp = int(timestamp_str)
    
    assert before <= timestamp <= after


def test_generate_request_id_contains_timestamp():
    """Test that request_id contains current timestamp."""
    before = int(time.time())
    request_id = generate_request_id()
    after = int(time.time())
    
    timestamp_str = request_id[1:11]
    timestamp = int(timestamp_str)
    
    assert before <= timestamp <= after


def test_generate_trace_id_has_random_hex():
    """Test that trace_id has 12 random hexadecimal characters."""
    trace_id = generate_trace_id()
    
    random_part = trace_id[11:]
    assert len(random_part) == 12
    assert all(c in '0123456789abcdef' for c in random_part)


def test_generate_request_id_has_random_hex():
    """Test that request_id has 12 random hexadecimal characters."""
    request_id = generate_request_id()
    
    random_part = request_id[11:]
    assert len(random_part) == 12
    assert all(c in '0123456789abcdef' for c in random_part)


def test_generate_trace_id_uniqueness():
    """Test that consecutive trace_ids are unique."""
    id1 = generate_trace_id()
    id2 = generate_trace_id()
    
    assert id1 != id2


def test_generate_request_id_uniqueness():
    """Test that consecutive request_ids are unique."""
    id1 = generate_request_id()
    id2 = generate_request_id()
    
    assert id1 != id2


def test_is_valid_trace_id_valid():
    """Test validation of valid trace_id."""
    assert is_valid_trace_id('t1735228800a1b2c3d4e5f6')
    assert is_valid_trace_id('t1234567890abcdef123456')


def test_is_valid_trace_id_invalid():
    """Test validation of invalid trace_id."""
    assert not is_valid_trace_id('t-1735228800-abc')
    assert not is_valid_trace_id('r1735228800a1b2c3d4e5f6')
    assert not is_valid_trace_id('t1735228800')
    assert not is_valid_trace_id('t1735228800ABC')
    assert not is_valid_trace_id('trace-123')
    assert not is_valid_trace_id('t173522880')
    assert not is_valid_trace_id('t1735228800a1b2c3d4e5f6g')


def test_is_valid_request_id_valid():
    """Test validation of valid request_id."""
    assert is_valid_request_id('r1735228800f6e5d4c3b2a1')
    assert is_valid_request_id('r1234567890fedcba987654')


def test_is_valid_request_id_invalid():
    """Test validation of invalid request_id."""
    assert not is_valid_request_id('r-1735228800-abc')
    assert not is_valid_request_id('t1735228800f6e5d4c3b2a1')
    assert not is_valid_request_id('r1735228800')
    assert not is_valid_request_id('r1735228800ABC')
    assert not is_valid_request_id('request-123')
    assert not is_valid_request_id('r173522880')
    assert not is_valid_request_id('r1735228800f6e5d4c3b2a1g')


def test_generate_span_id_format():
    """Test that generated span_id matches the expected format."""
    span_id = generate_span_id()

    assert span_id.startswith('s')
    assert len(span_id) == 9
    assert SPAN_ID_PATTERN.match(span_id)


def test_generate_span_id_has_random_hex():
    """Test that span_id has 8 random hexadecimal characters."""
    span_id = generate_span_id()

    random_part = span_id[1:]
    assert len(random_part) == 8
    assert all(c in '0123456789abcdef' for c in random_part)


def test_generate_span_id_uniqueness():
    """Test that consecutive span_ids are unique."""
    id1 = generate_span_id()
    id2 = generate_span_id()

    assert id1 != id2


def test_is_valid_span_id_valid():
    """Test validation of valid span_id."""
    assert is_valid_span_id('sa1b2c3d4')
    assert is_valid_span_id('s12345678')


def test_is_valid_span_id_invalid():
    """Test validation of invalid span_id."""
    assert not is_valid_span_id('s123')
    assert not is_valid_span_id('sABCD1234')
    assert not is_valid_span_id('span-123')
    assert not is_valid_span_id('sa1b2c3d4e')


def test_request_context_creation():
    """Test creating RequestContext with all fields."""
    ctx = RequestContext(
        trace_id='t1735228800a1b2c3d4e5f6',
        trace_source='GAPI:/api/orders',
        request_id='r1735228800f6e5d4c3b2a1',
        request_source='ORDER_SERVICE:/internal/orders',
        span_id='sa1b2c3d4',
        span_source='GAPI:POST/api/orders'
    )

    assert ctx.trace_id == 't1735228800a1b2c3d4e5f6'
    assert ctx.trace_source == 'GAPI:/api/orders'
    assert ctx.request_id == 'r1735228800f6e5d4c3b2a1'
    assert ctx.request_source == 'ORDER_SERVICE:/internal/orders'
    assert ctx.span_id == 'sa1b2c3d4'
    assert ctx.span_source == 'GAPI:POST/api/orders'
    assert ctx.parent_span_id is None


def test_request_context_with_parent_span():
    """Test creating RequestContext with parent_span_id."""
    ctx = RequestContext(
        trace_id='t1735228800a1b2c3d4e5f6',
        trace_source='GAPI:/api/orders',
        request_id='r1735228800f6e5d4c3b2a1',
        request_source='PULSE:/internal/orders',
        span_id='sb2c3d4e5',
        span_source='GAPI:POST/api/orders->PULSE:POST/internal/orders',
        parent_span_id='sa1b2c3d4'
    )

    assert ctx.span_id == 'sb2c3d4e5'
    assert ctx.parent_span_id == 'sa1b2c3d4'
    assert ctx.span_source == 'GAPI:POST/api/orders->PULSE:POST/internal/orders'


def test_request_context_to_dict():
    """Test converting RequestContext to dictionary."""
    ctx = RequestContext(
        trace_id='t1735228800a1b2c3d4e5f6',
        trace_source='GAPI:/api/orders',
        request_id='r1735228800f6e5d4c3b2a1',
        request_source='ORDER_SERVICE:/internal/orders',
        span_id='sa1b2c3d4',
        span_source='GAPI:POST/api/orders'
    )

    result = ctx.to_dict()

    assert result == {
        'trace_id': 't1735228800a1b2c3d4e5f6',
        'trace_source': 'GAPI:/api/orders',
        'request_id': 'r1735228800f6e5d4c3b2a1',
        'request_source': 'ORDER_SERVICE:/internal/orders',
        'span_id': 'sa1b2c3d4',
        'span_source': 'GAPI:POST/api/orders'
    }


def test_request_context_to_dict_with_parent_span():
    """Test converting RequestContext with parent_span_id to dictionary."""
    ctx = RequestContext(
        trace_id='t1735228800a1b2c3d4e5f6',
        trace_source='GAPI:/api/orders',
        request_id='r1735228800f6e5d4c3b2a1',
        request_source='PULSE:/internal/orders',
        span_id='sb2c3d4e5',
        span_source='GAPI:POST/api/orders->PULSE:POST/internal/orders',
        parent_span_id='sa1b2c3d4'
    )

    result = ctx.to_dict()

    assert result == {
        'trace_id': 't1735228800a1b2c3d4e5f6',
        'trace_source': 'GAPI:/api/orders',
        'request_id': 'r1735228800f6e5d4c3b2a1',
        'request_source': 'PULSE:/internal/orders',
        'span_id': 'sb2c3d4e5',
        'span_source': 'GAPI:POST/api/orders->PULSE:POST/internal/orders',
        'parent_span_id': 'sa1b2c3d4'
    }

