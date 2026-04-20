class LinearInterpolation:
    def __init__(self, known_points: list[tuple[float, float]]) -> None:
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