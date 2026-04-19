from nicegui import ui
import core.usecases.application.authentication as auth_usecases
from typing import Callable

class LogoutButton(ui.button):
    def __init__(self) -> None:
        super().__init__("Logout")

        self.on_click(self.execute)
    
    def execute(self) -> None:
        auth_usecases.log_out()
        ui.notify("Logged out successfully")
        ui.navigate.to("/login")

def build(template: Callable[[], None]) -> None:
    
    @ui.page("/dashboard")
    def dashboard() -> None:
        if not auth_usecases.is_logged_in():
            ui.navigate.to("/login")
            return
    
        template()

        with ui.row():
            ui.button(
                "Server Settings",
                on_click=lambda: ui.navigate.to("/server-settings")
            )

            LogoutButton()