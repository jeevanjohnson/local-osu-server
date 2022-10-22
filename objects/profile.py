from dataclasses import dataclass
from typing import Optional


@dataclass
class Profile:  # TODO: think about this more
    name: str
    avatar_url: Optional[str] = None
