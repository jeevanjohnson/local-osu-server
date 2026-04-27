from datetime import datetime
from nicegui import app, ui
from jays_tools.services import (
    Service, stop_services
)

from osu_snapshot.service import OsuSnapShotService
from proxy.service import ProxyService
from osu_watcher.service import OsuWatcherService
from interface.service import InterfaceService
from server.service import ServerService

# TODO: update management done here

SERVER_SERVICES: list[Service] = [
    ProxyService(),
    OsuWatcherService(),
    InterfaceService(),
    ServerService()
]

SCRIPT_SERVICES: list[Service] = [
    OsuSnapShotService(),
]


class FooterButtons:
    def __init__(self, server_service_cards: list["ServiceCard"]) -> None:
        self.server_service_cards = server_service_cards

        with ui.row():
            self.exit_btn = ui.button(
                "Shutdown Application",
                on_click=self.shutdown_application
            )
            self.exit_btn.set_background_color("red")
            with self.exit_btn:
                ui.tooltip(
                    "Safely shuts down application."
                )

            self.start_server_btn = ui.button(
                "Start Server",
                on_click=self.start_server
            )
            self.start_server_btn.set_background_color("green")
            with self.start_server_btn:
                ui.tooltip(
                    "Starts all necessary services for the server to run smoothly"
                )

            self.stop_server_btn = ui.button(
                "Stop Server",
                on_click=self.stop_server
            )
            with self.stop_server_btn:
                ui.tooltip(
                    "Stops all services related to the server"
                )

            self.stop_server_btn.disable()

    def shutdown_application(self) -> None:
        stop_services(SERVER_SERVICES)
        stop_services(SCRIPT_SERVICES)
        app.shutdown()

    def start_server(self) -> None:
        for service_service_card in self.server_service_cards:
            service_service_card.start_btn.run_method("click")

        self.start_server_btn.disable()
        self.stop_server_btn.enable()

    def stop_server(self) -> None:
        for service_service_card in self.server_service_cards:
            service_service_card.stop_btn.run_method("click")

        self.start_server_btn.enable()
        self.stop_server_btn.disable()


class ServiceCard(ui.card):
    def __init__(self, service: Service) -> None:
        super().__init__()
        self.service = service

        with self:
            ui.label(service.name)
            ui.label(service.description)
            self.status = ui.markdown("**Status**: Not Running")

            with ui.row():
                self.start_btn = ui.button("Start", on_click=self.start)
                self.start_btn.set_background_color("green")

                self.stop_btn = ui.button("Stop", on_click=self.stop)
                self.stop_btn.set_background_color("red")

        self.sync_ui()

    def sync_ui(self) -> None:
        alive_and_up = self.service.is_running() and self.service.is_ready()
        getting_ready = self.service.is_running() and not self.service.is_ready()
        not_running = not self.service.is_running()

        if alive_and_up:
            self.start_btn.disable()
            self.stop_btn.enable()
            self.status.set_content("**Status**: Running")
        elif getting_ready:
            self.start_btn.disable()
            self.stop_btn.disable()
            self.status.set_content("**Status**: Getting Ready...")
        elif not_running:
            self.start_btn.enable()
            self.stop_btn.disable()
            self.status.set_content("**Status**: Not Running")

    def start(self) -> None:
        self.service.start()
        self.sync_ui()
        self.ready_timer = ui.timer(0.5, self.check_till_ready)

    def stop(self) -> None:
        self.service.stop()
        self.sync_ui()

    def check_till_ready(self) -> None:
        if self.service.is_ready():
            self.ready_timer.cancel()

        self.sync_ui()


class CurrentTime(ui.markdown):
    def __init__(self) -> None:
        super().__init__()

        self.update_time()
        self.timer = ui.timer(1.0, self.update_time)

    def update_time(self) -> None:
        self.set_content(f"*current time: {datetime.now():%X}*")


def build_ui() -> None:
    ui.markdown("# LOS! Control Panel")

    ui.separator()

    CurrentTime()

    ui.separator()

    ui.markdown("## Services")

    server_service_cards: list[ServiceCard] = []

    with ui.grid(columns=3):
        for server_service in SERVER_SERVICES:
            server_service_cards.append(
                ServiceCard(server_service)
            )

    ui.separator()

    ui.markdown("## Scripts")

    with ui.grid(columns=3):
        for script_service in SCRIPT_SERVICES:
            ServiceCard(script_service)

    ui.separator()

    FooterButtons(server_service_cards)


if __name__ in {
    "__main__",
    "__mp_main__",  # multiprocessing compatibility
}:
    build_ui()
    try:
        ui.run(
            title="LOS! Control Panel",
            dark=True,
            frameless=True,
            native=True,
            reload=False,
            show=True,
        )
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        stop_services(SERVER_SERVICES)
        stop_services(SCRIPT_SERVICES)
