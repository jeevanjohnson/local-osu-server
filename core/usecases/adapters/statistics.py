class PowerLawInterpolation:
    def __init__(
            self, 
            known_points: list[tuple[float, float]] | list[tuple[int, int]]
        ) -> None:
        # assumes x is the input and y is the output
        # (x, y) = (input, output)

        self.known_points = known_points
        
        self.known_points.sort(key=lambda point: point[0]) 
        self.inputs = [point[0] for point in self.known_points]
        self.outputs = [point[1] for point in self.known_points]
    
    def approximate(self, input_value: float, clamp: bool = True) -> float:
        if not self.known_points:
            raise ValueError("points cannot be empty")
        
        # For within-range values, use linear interpolation
        if self.inputs[0] <= input_value <= self.inputs[-1]:
            # Standard linear interpolation
            for i in range(len(self.inputs) - 1):
                if self.inputs[i] <= input_value <= self.inputs[i + 1]:
                    x1, y1 = self.inputs[i], self.outputs[i]
                    x2, y2 = self.inputs[i + 1], self.outputs[i + 1]
                    if x2 == x1:
                        return (y1 + y2) / 2
                    else:
                        return y1 + (input_value - x1) * (y2 - y1) / (x2 - x1)
            return self.outputs[-1]
        
        # For out-of-range extrapolation, use smart approach
        if clamp:
            # Clamp to nearest data point
            if input_value < self.inputs[0]:
                return self.outputs[0]
            else:
                return self.outputs[-1]
        else:
            # Smart extrapolation based on data distribution
            if input_value < self.inputs[0]:
                # Below minimum - look at first 10-20% of data to estimate trend
                middle_idx = len(self.inputs) // 5  # Look at first 20%
                if middle_idx >= 1:
                    # Calculate average "spacing" in this region
                    pp_range = self.inputs[middle_idx] - self.inputs[0]
                    rank_range = self.outputs[middle_idx] - self.outputs[0]
                    
                    if pp_range > 0:
                        # Average change in rank per PP in the populated region
                        avg_slope = rank_range / pp_range
                    else:
                        avg_slope = 0
                    
                    # Extrapolate using this slope
                    extrapolated = self.outputs[0] + (input_value - self.inputs[0]) * avg_slope
                    return extrapolated
                else:
                    return self.outputs[0]
            else:
                # Above maximum - use last observable trend
                if len(self.inputs) >= 2:
                    # Use slope from last 1% of data
                    start_idx = max(0, len(self.inputs) - max(1, len(self.inputs) // 100))
                    pp_range = self.inputs[-1] - self.inputs[start_idx]
                    rank_range = self.outputs[-1] - self.outputs[start_idx]
                    
                    if pp_range > 0:
                        avg_slope = rank_range / pp_range
                    else:
                        avg_slope = 0
                    
                    extrapolated = self.outputs[-1] + (input_value - self.inputs[-1]) * avg_slope
                    return extrapolated
                else:
                    return self.outputs[-1]

            raise ValueError("Input is out of bounds of known points")

class LinearInterpolation:
    def __init__(
            self, 
            known_points: list[tuple[float, float]] | list[tuple[int, int]]
        ) -> None:
        # assumes x is the input and y is the output
        # (x, y) = (input, output)

        self.known_points = known_points
        
        self.known_points.sort(key=lambda point: point[0]) 
        self.inputs = [point[0] for point in self.known_points]
        self.outputs = [point[1] for point in self.known_points]
    
    def approximate(self, input: float, clamp: bool = True) -> float:
        # Single point case
        if len(self.inputs) == 1:
            return self.outputs[0]

        # Clamping mode
        if clamp:
            if input <= self.inputs[0]:
                return self.outputs[0]
            if input >= self.inputs[-1]:
                return self.outputs[-1]
        else:
            # Extrapolation mode (linear extension)
            if input <= self.inputs[0]:
                x0, x1 = self.inputs[0], self.inputs[1]
                y0, y1 = self.outputs[0], self.outputs[1]
                return y0 + (y1 - y0) * (input - x0) / (x1 - x0)
            if input >= self.inputs[-1]:
                x0, x1 = self.inputs[-2], self.inputs[-1]
                y0, y1 = self.outputs[-2], self.outputs[-1]
                return y0 + (y1 - y0) * (input - x0) / (x1 - x0)

        # Interpolate within range
        for i in range(len(self.inputs) - 1):
            if self.inputs[i] <= input <= self.inputs[i + 1]:
                x0, x1 = self.inputs[i], self.inputs[i + 1]
                y0, y1 = self.outputs[i], self.outputs[i + 1]
                return y0 + (y1 - y0) * (input - x0) / (x1 - x0)

        raise ValueError("Unexpected error: input not in any interval")