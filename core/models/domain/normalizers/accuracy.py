from jays_tools.architecture import DomainModel


class Accuracy(float, DomainModel):
    def __new__(cls, value: float) -> "Accuracy":
        if not 0.0 <= value <= 1.0:
            raise ValueError("Accuracy must be between 0.0 and 1.0")

        return super().__new__(cls, value)

    def to_percentage(self) -> float:
        return self * 100

    @classmethod
    def from_percetage(cls, value: float) -> float:
        return cls(value / 100)
