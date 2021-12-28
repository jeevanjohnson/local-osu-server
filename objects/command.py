from typing import Callable
from typing import Optional

class Command:
    def __init__(
        self, name: str, func: Callable,
        docs: Optional[str] = None,
        confirm_with_user: bool = False,
        names: Optional[list[str]] = None
    ) -> None:
        self.func = func
        self.name = name
        self.docs = docs
        self.confirm_with_user = confirm_with_user

        if names:
            self.names = names
            if self.name not in self.names:
                self.names.append(self.name)
        else:
            self.names = [self.name]

        self.args: list[str] = []