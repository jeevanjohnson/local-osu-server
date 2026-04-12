import math
from typing import Callable, Sequence

DATA_POINT = tuple[float, float]  # (x, y)


def linear_interpolation(
    input_value: float,
    points: Sequence[DATA_POINT],
    input_key: Callable[[DATA_POINT], float] = lambda p: p[0],
    output_key: Callable[[DATA_POINT], float] = lambda p: p[1],
    clamp: bool = True,
) -> float:
    """
    TLDR:
    - Generates a curve of best fit through a set of known data points and uses it to estimate the output for a given input.
    - If the input is outside the range of the known data, it can either clamp to the nearest endpoint or perform linear extrapolation.
    - This is NOT linear regression, as linear regression doesn't care about hitting any known points exactly, its more concerned
    with minimizing overall error across all points.

    Perform linear interpolation (or extrapolation) on a set of points.

    Parameters
    ----------
    input_value : float
        The input value for which we want the corresponding output.
    points : List[T]
        A list of data points. Each point can be any type (tuple, dict, object).
    input_key : Callable[[T], float], optional
        Function that extracts the input coordinate from a point. Default assumes point[0].
    output_key : Callable[[T], float], optional
        Function that extracts the output coordinate from a point. Default assumes point[1].
    clamp : bool, optional
        If True (default), values outside the range of input in the data are clamped to
        the nearest endpoint output. If False, linear extrapolation is performed.
    round_result : bool, optional
        If True, the result is rounded to the nearest integer. Default is False.

    Returns
    -------
    float
        The interpolated (or extrapolated) output value.
    """
    if not points:
        raise ValueError("points cannot be empty")

    # Sort points by input coordinate (independent variable)
    sorted_points = sorted(points, key=input_key)

    inputs = [input_key(p) for p in sorted_points]
    outputs = [output_key(p) for p in sorted_points]

    # Handle cases where target input is outside the data range
    if input_value <= inputs[0]:
        if clamp:
            return outputs[0]
        else:
            # Extrapolate using two points that have different inputs AND outputs
            # This skips flat/vertical regions in the data
            for i in range(len(inputs) - 1):
                if inputs[i] != inputs[i + 1] and outputs[i] != outputs[i + 1]:
                    slope = (outputs[i + 1] - outputs[i]) / (inputs[i + 1] - inputs[i])
                    return outputs[i] + (input_value - inputs[i]) * slope
            # If can't find two varying points, can't extrapolate
            return outputs[0]

    if input_value >= inputs[-1]:
        if clamp:
            return outputs[-1]
        else:
            # Extrapolate using two points that have different inputs AND outputs
            for i in range(len(inputs) - 1, 0, -1):
                if inputs[i] != inputs[i - 1] and outputs[i] != outputs[i - 1]:
                    slope = (outputs[i] - outputs[i - 1]) / (inputs[i] - inputs[i - 1])
                    return outputs[i - 1] + (input_value - inputs[i - 1]) * slope
            # If can't find two varying points, can't extrapolate
            return outputs[-1]

    # Find the interval containing input_value
    for i in range(len(inputs) - 1):
        if inputs[i] <= input_value <= inputs[i + 1]:
            x1, y1 = inputs[i], outputs[i]
            x2, y2 = inputs[i + 1], outputs[i + 1]
            if x2 == x1:  # vertical segment – use average output
                result = (y1 + y2) / 2
            else:
                result = y1 + (input_value - x1) * (y2 - y1) / (x2 - x1)
            return result

    # Should never reach here
    raise RuntimeError("Unexpected error during interpolation")


def logarithmic_interpolation(
    input_value: float,
    points: Sequence[DATA_POINT],
    input_key: Callable[[DATA_POINT], float] = lambda p: p[0],
    output_key: Callable[[DATA_POINT], float] = lambda p: p[1],
    clamp: bool = True,
) -> float:
    """
    Perform logarithmic interpolation on a set of points.

    Converts output values to log space, performs linear interpolation there,
    then converts back to linear space. This is better for exponential/power-law
    distributions like osu! PP vs rank.

    Parameters
    ----------
    input_value : float
        The input value for which we want the corresponding output.
    points : List[T]
        A list of data points. Each point can be any type (tuple, dict, object).
    input_key : Callable[[T], float], optional
        Function that extracts the input coordinate from a point.
    output_key : Callable[[T], float], optional
        Function that extracts the output coordinate from a point.
    clamp : bool, optional
        If True, values outside range are clamped to nearest endpoint.
        If False, logarithmic extrapolation is performed.

    Returns
    -------
    float
        The interpolated (or extrapolated) output value.
    """
    if not points:
        raise ValueError("points cannot be empty")

    # Sort points by input coordinate
    sorted_points = sorted(points, key=input_key)

    inputs = [input_key(p) for p in sorted_points]
    outputs = [output_key(p) for p in sorted_points]

    # Convert outputs to log scale (with safety check for values <= 0)
    log_outputs = []
    for out in outputs:
        if out <= 0:
            log_outputs.append(0)  # fallback for non-positive values
        else:
            log_outputs.append(math.log(out))

    # Handle cases where target input is outside the data range
    if input_value <= inputs[0]:
        if clamp:
            return outputs[0]
        else:
            # Extrapolate using the last two DISTINCT points
            # (in case there are duplicate input values at the tail)
            slope = None
            for i in range(len(inputs) - 1, 0, -1):
                if inputs[i] != inputs[i - 1]:
                    slope = (log_outputs[i] - log_outputs[i - 1]) / (
                        inputs[i] - inputs[i - 1]
                    )
                    log_result = (
                        log_outputs[i - 1] + (input_value - inputs[i - 1]) * slope
                    )
                    return math.exp(log_result)
            # If all inputs are the same, can't extrapolate
            return outputs[0]

    if input_value >= inputs[-1]:
        if clamp:
            return outputs[-1]
        else:
            # Extrapolate using log space, finding two points that are actually different
            # Skip the flat tail region where outputs don't change
            for i in range(len(inputs) - 1, 0, -1):
                if outputs[i] != outputs[i - 1]:  # Find where output actually changes
                    slope = (log_outputs[i] - log_outputs[i - 1]) / (
                        inputs[i] - inputs[i - 1]
                    )
                    log_result = (
                        log_outputs[i - 1] + (input_value - inputs[i - 1]) * slope
                    )
                    return math.exp(log_result)
            # If all outputs are the same, can't extrapolate
            return outputs[0]

    # Find the interval containing input_value
    for i in range(len(inputs) - 1):
        if inputs[i] <= input_value <= inputs[i + 1]:
            x1, y_log1 = inputs[i], log_outputs[i]
            x2, y_log2 = inputs[i + 1], log_outputs[i + 1]

            if x2 == x1:
                # vertical segment – use average of log outputs
                result = math.exp((y_log1 + y_log2) / 2)
            else:
                # Linear interpolation in log space
                log_result = y_log1 + (input_value - x1) * (y_log2 - y_log1) / (x2 - x1)
                result = math.exp(log_result)
            return result

    # Should never reach here
    raise RuntimeError("Unexpected error during logarithmic interpolation")


def power_law_interpolation(
    input_value: float,
    points: Sequence[DATA_POINT],
    input_key: Callable[[DATA_POINT], float] = lambda p: p[0],
    output_key: Callable[[DATA_POINT], float] = lambda p: p[1],
    clamp: bool = True,
) -> float:
    """
    Perform smart interpolation tailored for osu! PP vs rank distribution.

    Instead of fitting a mathematical model, this uses the actual data distribution
    to extrapolate smoothly. For PP outside the data range, it estimates based on:
    1. The observed PP density in the data (players per PP bracket)
    2. Assumes similar density continues below the lowest observed PP

    Parameters
    ----------
    input_value : float
        The input value for which we want the corresponding output.
    points : Sequence[T]
        A list of data points. Each point can be any type (tuple, dict, object).
    input_key : Callable[[T], float], optional
        Function that extracts the input coordinate from a point.
    output_key : Callable[[T], float], optional
        Function that extracts the output coordinate from a point.
    clamp : bool, optional
        If True, values outside range are clamped to nearest endpoint.
        If False, uses smart extrapolation.

    Returns
    -------
    float
        The interpolated (or extrapolated) output value.
    """
    if not points:
        raise ValueError("points cannot be empty")

    # Extract and sort points by input coordinate
    sorted_points = sorted(points, key=input_key)
    inputs = [input_key(p) for p in sorted_points]
    outputs = [output_key(p) for p in sorted_points]

    # For within-range values, use linear interpolation
    if inputs[0] <= input_value <= inputs[-1]:
        # Standard linear interpolation
        for i in range(len(inputs) - 1):
            if inputs[i] <= input_value <= inputs[i + 1]:
                x1, y1 = inputs[i], outputs[i]
                x2, y2 = inputs[i + 1], outputs[i + 1]
                if x2 == x1:
                    return (y1 + y2) / 2
                else:
                    return y1 + (input_value - x1) * (y2 - y1) / (x2 - x1)
        return outputs[-1]

    # For out-of-range extrapolation, use smart approach
    if clamp:
        # Clamp to nearest data point
        if input_value < inputs[0]:
            return outputs[0]
        else:
            return outputs[-1]
    else:
        # Smart extrapolation based on data distribution
        if input_value < inputs[0]:
            # Below minimum - look at first 10-20% of data to estimate trend
            middle_idx = len(inputs) // 5  # Look at first 20%
            if middle_idx >= 1:
                # Calculate average "spacing" in this region
                pp_range = inputs[middle_idx] - inputs[0]
                rank_range = outputs[middle_idx] - outputs[0]

                if pp_range > 0:
                    # Average change in rank per PP in the populated region
                    avg_slope = rank_range / pp_range
                else:
                    avg_slope = 0

                # Extrapolate using this slope
                extrapolated = outputs[0] + (input_value - inputs[0]) * avg_slope
                return extrapolated
            else:
                return outputs[0]
        else:
            # Above maximum - use last observable trend
            if len(inputs) >= 2:
                # Use slope from last 1% of data
                start_idx = max(0, len(inputs) - max(1, len(inputs) // 100))
                pp_range = inputs[-1] - inputs[start_idx]
                rank_range = outputs[-1] - outputs[start_idx]

                if pp_range > 0:
                    avg_slope = rank_range / pp_range
                else:
                    avg_slope = 0

                extrapolated = outputs[-1] + (input_value - inputs[-1]) * avg_slope
                return extrapolated
            else:
                return outputs[-1]
