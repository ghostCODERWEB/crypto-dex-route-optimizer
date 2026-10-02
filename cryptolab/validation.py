"""Explicit primitive validation for synthetic economic and state-machine inputs."""

from decimal import Decimal, InvalidOperation
import math


def integer(value, minimum=0, maximum=None):
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        raise ValueError("integer out of allowed range")
    return value


def decimal(value, positive=False, signed=False):
    if isinstance(value, bool):
        raise ValueError("boolean is not a decimal")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid decimal")
    if (
        not result.is_finite()
        or (not signed and result < 0)
        or (positive and result <= 0)
    ):
        raise ValueError("decimal out of range")
    return result


def finite(value, positive=False, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError("boolean is not a number")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError("invalid number")
    if (
        not math.isfinite(result)
        or (positive and result <= 0)
        or (nonnegative and result < 0)
    ):
        raise ValueError("number out of range")
    return result


def identifier(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError("nonempty identifier up to 200 characters required")
    return value


def chronological(events):
    if not isinstance(events, list) or len(events) > 10000:
        raise ValueError("event list of at most 10000 items required")
    previous = 0
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("event must be an object")
        timestamp = integer(event["timestamp"])
        if timestamp < previous:
            raise ValueError("events must be chronological")
        previous = timestamp
    return events
