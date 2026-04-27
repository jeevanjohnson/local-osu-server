import sys  # noqa
from pathlib import Path  # noqa

sys.path.append(str(Path(__file__).parent.parent))  # noqa

from nicegui import ui
from typing import Callable
from core.usecases.domain.authentication import AuthenticationDomainUseCase

AUTHENTICATION_DOMAIN_USECASE = AuthenticationDomainUseCase()


def build(template: Callable[[], None]) -> None:

    @ui.page("/")
    async def homepage() -> None:
        template()

        if await AUTHENTICATION_DOMAIN_USECASE.is_logged_in():
            ui.navigate.to("/dashboard")
        else:
            ui.navigate.to("/login")
