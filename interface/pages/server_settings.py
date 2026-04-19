from typing import Callable

from nicegui import ui

import core.usecases.domain.server_settings as server_settings_usecases

class InputStyle(ui.input):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.classes("w-96")
        self.style("background-color: #1c1c1c; color: #ffffff;")
        self.props("outlined")

class OsuAPIClientIDInput(InputStyle):
    def __init__(self) -> None:
        super().__init__("Osu! API Client ID")

        self.value = server_settings_usecases.get_osu_api_v2_client_id()

        self.on_value_change(self.update_client_id)

    def update_client_id(self) -> None:
        try:
            client_id = self.value or None
            if client_id is not None:
                client_id = int(client_id)

            server_settings_usecases.update_osu_api_client_id(client_id)
            ui.notify(f"Osu! API Client ID updated successfully to: {client_id}")
        except ValueError:
            ui.notify("Please enter a valid Osu! API Client ID")

class OsuAPIClientSecretInput(InputStyle):
    def __init__(self) -> None:
        super().__init__("Osu! API Client Secret", password=True)

        self.value = server_settings_usecases.get_osu_api_v2_client_secret()

        self.on_value_change(self.update_client_secret)

    def update_client_secret(self) -> None:
        client_secret = self.value or None
        server_settings_usecases.update_osu_api_client_secret(client_secret)

        ui.notify(f"Osu! API Client Secret updated successfully!")

def build(template: Callable[[], None]) -> None:
    
    @ui.page("/server-settings")
    def server_settings() -> None:
        template()

        with ui.column().classes("flex items-center justify-center w-full min-h-screen gap-6"):

            with ui.column().classes("items-center gap-4"):

                ui.markdown("# Server Settings")

                ui.separator().classes("w-96")

                OsuAPIClientIDInput()
                OsuAPIClientSecretInput()

            ui.separator().classes("w-96")

            ui.button(
                "Previous Page",
                on_click=ui.navigate.back
            )