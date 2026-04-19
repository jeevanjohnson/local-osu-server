from nicegui import ui
from typing import Callable
import core.usecases.application.authentication as auth_usecases

def build(template: Callable[[], None]) -> None:
    
    @ui.page("/")
    def homepage() -> None:
        template()

        if auth_usecases.is_logged_in():
            ui.navigate.to("/dashboard")
        else:
            ui.navigate.to("/login")
        
