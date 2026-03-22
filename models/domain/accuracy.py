from typing import Annotated

from pydantic import AfterValidator


def _validate_unit_accuracy(value: float) -> float:
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError("Accuracy must be between 0.0 and 1.0")
    return value


UnitAccuracy = Annotated[float, AfterValidator(_validate_unit_accuracy)]


def to_unit_accuracy(value: float | int) -> float:
    numeric = float(value)

    if 0.0 <= numeric <= 1.0:
        return numeric

    # Backward compatibility for legacy percentage values persisted in profiles.
    if 1.0 < numeric <= 100.0:
        return numeric / 100.0

    raise ValueError("Accuracy must be in 0..1 internally, or 0..100 for conversion")


def to_percentage(accuracy: UnitAccuracy) -> float:
    return float(accuracy) * 100.0
