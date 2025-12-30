"""Order splitting algorithm for Pulse.

This module implements the quantity and time distribution logic described in
`doc/requirements/split_order_feature.md`.

It is intentionally pure (no database access). The background worker will use
this to calculate per-slice quantities and scheduled times, then persist them
via repositories.

TODO: Integrate this module with the Pulse background splitting worker once it
is implemented.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List


@dataclass(frozen=True)
class SplitSlice:
    """Represents one child slice of a parent order."""

    quantity: int
    sequence_number: int
    scheduled_at: datetime


def calculate_split_schedule(
    parent_created_at: datetime,
    total_quantity: int,
    num_splits: int,
    duration_minutes: int,
    randomize: bool,
) -> List[SplitSlice]:
    """Calculate quantities and scheduled times for child orders.

    Follows the algorithm specified in doc/requirements/split_order_feature.md.

    All scheduled_at values are within the inclusive window:
        [parent_created_at, parent_created_at + duration_minutes].

    Args:
        parent_created_at: When the parent order was created (assumed UTC).
        total_quantity: Total shares to trade.
        num_splits: Number of child orders.
        duration_minutes: Total duration window in minutes.
        randomize: Whether to apply quantity and time variance.

    Returns:
        List of SplitSlice objects, one per child, in sequence order.

    Raises:
        ValueError: If inputs are invalid.
    """
    if num_splits <= 0:
        raise ValueError("num_splits must be >= 1")
    if total_quantity <= 0:
        raise ValueError("total_quantity must be > 0")
    if duration_minutes < 0:
        raise ValueError("duration_minutes must be >= 0")

    # Ensure timestamp is treated as UTC to avoid surprises.
    if parent_created_at.tzinfo is None:
        parent_created_at = parent_created_at.replace(tzinfo=timezone.utc)
    else:
        parent_created_at = parent_created_at.astimezone(timezone.utc)

    base_quantity = total_quantity / num_splits

    # Step 1: Calculate quantities.
    quantities: list[int] = []
    if randomize and num_splits > 1:
        # Apply ±20% variance to all but last; last gets the remainder.
        for _ in range(num_splits - 1):
            variance = random.uniform(-0.2, 0.2)
            qty = int(base_quantity * (1 + variance))
            if qty < 0:
                qty = 0
            quantities.append(qty)
    else:
        # Equal distribution with integer rounding; last gets the remainder.
        for _ in range(num_splits - 1):
            quantities.append(int(base_quantity))

    last_qty = total_quantity - sum(quantities)
    quantities.append(last_qty)

    # Step 2: Calculate scheduled times.
    time_window_end = parent_created_at + timedelta(minutes=duration_minutes)
    base_interval_minutes = (
        duration_minutes / (num_splits - 1) if num_splits > 1 else 0.0
    )

    scheduled_times: list[datetime] = []
    for i in range(num_splits):
        base_time = parent_created_at + timedelta(
            minutes=(i * base_interval_minutes)
        )

        # Randomize internal slices only when enabled.
        if randomize and num_splits > 1 and 0 < i < num_splits - 1:
            max_variance = base_interval_minutes * 0.3
            variance_minutes = random.uniform(-max_variance, max_variance)
            scheduled_time = base_time + timedelta(minutes=variance_minutes)
        else:
            scheduled_time = base_time

        # Enforce hard time window boundaries.
        if scheduled_time < parent_created_at:
            scheduled_time = parent_created_at
        if scheduled_time > time_window_end:
            scheduled_time = time_window_end

        scheduled_times.append(scheduled_time)

    if len(quantities) != num_splits or len(scheduled_times) != num_splits:
        # Internal safeguard; this should never happen.
        raise RuntimeError("Mismatch between number of splits and results")

    slices = [
        SplitSlice(
            quantity=quantities[i],
            sequence_number=i + 1,
            scheduled_at=scheduled_times[i],
        )
        for i in range(num_splits)
    ]

    # Final validation to match spec guarantees.
    assert sum(s.quantity for s in slices) == total_quantity
    assert all(
        parent_created_at <= s.scheduled_at <= time_window_end for s in slices
    )

    return slices


# Helpers for converting between Unix microseconds (DB representation) and
# Python datetime.

_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def micros_to_datetime(value: int) -> datetime:
    """Convert Unix microseconds to an aware UTC datetime.

    This avoids floating-point arithmetic by using integer microseconds.

    TODO: Use this helper when reading BIGINT timestamps from the database.
    """
    if value < 0:
        raise ValueError("Unix microseconds must be >= 0")
    return _UNIX_EPOCH + timedelta(microseconds=value)


def datetime_to_micros(dt: datetime) -> int:
    """Convert a datetime to Unix microseconds since epoch (UTC).

    Naive datetimes are treated as UTC. Conversion uses integer arithmetic
    only, to preserve microsecond precision.

    TODO: Use this helper when writing BIGINT timestamps to the database.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    delta = dt - _UNIX_EPOCH
    return (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )

