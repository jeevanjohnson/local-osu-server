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
            # Extrapolate using the first two points
            if inputs[0] == inputs[1]:
                return outputs[0]  # vertical line – can't extrapolate
            slope = (outputs[1] - outputs[0]) / (inputs[1] - inputs[0])
            return outputs[0] + (input_value - inputs[0]) * slope

    if input_value >= inputs[-1]:
        if clamp:
            return outputs[-1]
        else:
            # Extrapolate using the last two points
            if inputs[-2] == inputs[-1]:
                return outputs[-1]
            slope = (outputs[-1] - outputs[-2]) / (inputs[-1] - inputs[-2])
            return outputs[-1] + (input_value - inputs[-1]) * slope

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
