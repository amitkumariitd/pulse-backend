"""Unit tests for the order splitting algorithm.

These tests focus on the pure calculation logic in `pulse.splitting`.
"""

from datetime import datetime, timedelta, timezone

import pytest

from pulse.splitting import (
    SplitSlice,
    calculate_split_schedule,
)


def _dt(year, month, day, hour, minute):
    """Helper to create an aware UTC datetime.

    Keeps tests concise.
    """
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_equal_splits_no_randomization():
    """Equal quantity and evenly spaced times when randomize is False."""
    parent_created_at = _dt(2025, 12, 29, 10, 0)
    total_quantity = 100
    num_splits = 5
    duration_minutes = 60

    slices = calculate_split_schedule(
        parent_created_at=parent_created_at,
        total_quantity=total_quantity,
        num_splits=num_splits,
        duration_minutes=duration_minutes,
        randomize=False,
    )

    assert len(slices) == num_splits
    assert sum(s.quantity for s in slices) == total_quantity

    # Base interval: 60 / (5 - 1) = 15 minutes
    expected_interval = timedelta(minutes=15)
    for i, s in enumerate(slices):
        assert s.sequence_number == i + 1
        assert s.scheduled_at == parent_created_at + i * expected_interval


def test_randomized_splits_respect_time_window():
    """Randomized schedule stays within the required time window."""
    parent_created_at = _dt(2025, 12, 29, 10, 0)
    total_quantity = 200
    num_splits = 6
    duration_minutes = 90

    slices = calculate_split_schedule(
        parent_created_at=parent_created_at,
        total_quantity=total_quantity,
        num_splits=num_splits,
        duration_minutes=duration_minutes,
        randomize=True,
    )

    assert len(slices) == num_splits
    assert sum(s.quantity for s in slices) == total_quantity

    window_end = parent_created_at + timedelta(minutes=duration_minutes)

    for s in slices:
        assert isinstance(s, SplitSlice)
        assert parent_created_at <= s.scheduled_at <= window_end

    # First slice should be at the start, last at or near the end (no randomization
    # applied to first/last, per spec).
    assert slices[0].scheduled_at == parent_created_at
    assert slices[-1].scheduled_at == window_end


def test_single_split_degenerates_to_parent_time():
    """Single split uses parent_created_at and full quantity."""
    parent_created_at = _dt(2025, 12, 29, 10, 0)
    total_quantity = 50

    slices = calculate_split_schedule(
        parent_created_at=parent_created_at,
        total_quantity=total_quantity,
        num_splits=1,
        duration_minutes=30,
        randomize=True,  # Has no effect for single split
    )

    assert len(slices) == 1
    assert slices[0].quantity == total_quantity
    assert slices[0].scheduled_at == parent_created_at


@pytest.mark.parametrize(
    "total_quantity,num_splits,duration_minutes",
    [(-1, 5, 60), (100, 0, 60), (100, 5, -1)],
)
def test_invalid_inputs_raise_value_error(
    total_quantity: int, num_splits: int, duration_minutes: int
):
    """Guard-rail validation for obviously invalid inputs."""
    parent_created_at = _dt(2025, 12, 29, 10, 0)

    with pytest.raises(ValueError):
        calculate_split_schedule(
            parent_created_at=parent_created_at,
            total_quantity=total_quantity,
            num_splits=num_splits,
            duration_minutes=duration_minutes,
            randomize=False,
        )


