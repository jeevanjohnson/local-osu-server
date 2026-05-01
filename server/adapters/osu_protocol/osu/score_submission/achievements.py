from dataclasses import dataclass


@dataclass
class Achievement:
    image_url: str
    title: str
    description: str

    def serialize(self) -> str:
        return f"{self.image_url}+{self.title}+{self.description}"


class Achievements(list[Achievement]):
    def serialize(self) -> str:
        return "/".join(achievement.serialize() for achievement in self)
