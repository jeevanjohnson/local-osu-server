class Accuracy(float):
    def __new__(cls, value: float) -> "Accuracy":
        return super().__new__(cls, max(0.0, min(1.0, value)))
    
    def to_percentage(self) -> float:
        return self * 100