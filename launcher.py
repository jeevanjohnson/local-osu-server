import multiprocessing
from datetime import datetime
from typing import Any, Callable

from nicegui import app, ui
from jays_tools import JsonDatabase, MigratableModel

import osu_watcher.main as osu_watcher
import proxy.main as proxy
import interface.main as interface
import server.main as server
import osu_scraper.main as osu_scraper

from core.constants import LAUNCHER_STATE

class LauncherState(MigratableModel):
    dev_mode: bool = False

STATE_DB = JsonDatabase(
    path=LAUNCHER_STATE,
    database_model=LauncherState,
)

# TODO: update management will be done here not in the server

class ApplicationService:
    def __init__(
        self,
        name: str,
        description: str,
        service_start: Callable[[bool], Any],
        service_stop: Callable[[bool], Any]
    ) -> None:
        self.name = name
        self.description = description
        self.service_start = service_start
        self.service_stop = service_stop
        self.running = False
        self.process: multiprocessing.Process | None = None

    def get_launch_process(self, dev_mode: bool = False) -> multiprocessing.Process:
        if self.process is None:
            self.process = multiprocessing.Process(target=self.service_start, args=(dev_mode,))
            
        return self.process

    def start(self) -> None:
        launcher_state = STATE_DB.get_database()
        process = self.get_launch_process(dev_mode=launcher_state.dev_mode)
        process.start()
        self.running = True

    def stop(self) -> None:
        launcher_state = STATE_DB.get_database()
        process = self.get_launch_process(dev_mode=launcher_state.dev_mode)

        if process.is_alive():
            process.terminate()
            process.join(timeout=5)

        self.process = None
        self.service_stop(launcher_state.dev_mode)
        self.running = False

SERVICES: list[ApplicationService] = [
    ApplicationService(
        name="Proxy",
        description="The proxy process which allows the osu! client to connect to the server.",
        service_start=proxy.start,
        service_stop=proxy.stop,
    ),
    ApplicationService(
        name="Osu! Watcher",
        description="The osu! watcher process watches for live changes on osu! client actions.",
        service_start=osu_watcher.start,
        service_stop=osu_watcher.stop,
    ),
    ApplicationService(
        name="LOS Interface",
        description="The user interface for interacting with your LOS! profiles and more.",
        service_start=interface.start,
        service_stop=interface.stop,
    ),
    ApplicationService(
        name="Server",
        description="The server which the osu! client connects to.",
        service_start=server.start,
        service_stop=server.stop,
    ),
    ApplicationService(
        name="Osu! Scraper",
        description="A scraper used to provide accurate ranking based of in-game pp. Please run once in a while to keep performance data up to date.",
        service_start=osu_scraper.start,
        service_stop=osu_scraper.stop,
    ),
]


class ServiceButton(ui.button):
    def __init__(self, service: ApplicationService, *args, **kwargs) -> None:
        self.service = service
        super().__init__(f"Start {self.service.name} service", *args, **kwargs)
        self.on_click(self.execute)

        self.set_background_color("green")

    def start_service(self) -> None:
        self.service.start()
        ui.notify(f"{self.service.name} service started")

    def stop_service(self) -> None:
        self.service.stop()
        ui.notify(f"{self.service.name} service stopped")

    def execute(self) -> None:
        if self.service.running:
            self.text = f"Start {self.service.name} service"
            self.set_background_color("green")
            self.stop_service()
        else:
            self.text = f"Stop {self.service.name} service"
            self.set_background_color("red")
            self.start_service()


class ExitButton(ui.button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__("Shutdown", *args, **kwargs)
        self.on_click(self.exit)

        self.set_background_color("red")

    def exit(self) -> None:
        for service in SERVICES:
            if service.running:
                service.stop()

        app.shutdown()

class DevModeToggle(ui.button):
    def __init__(self, *args, **kwargs) -> None:
        launcher_state = STATE_DB.get_database()

        if launcher_state.dev_mode is True:
            button_text = "Turn Dev Mode OFF"
            color = "red"
        else:
            button_text = "Turn Dev Mode ON"
            color = "blue"
        
        super().__init__(button_text, *args, **kwargs)
        self.set_background_color(color)

        self.on_click(self.toggle)

    def toggle(self) -> None:
        if any(service.running for service in SERVICES):
            ui.notify("Please stop all running services before toggling developer mode.")
            return

        launcher_state = STATE_DB.get_database()
        launcher_state.dev_mode = not launcher_state.dev_mode
        STATE_DB.update_database(launcher_state)

        if launcher_state.dev_mode is True:
            self.text = "Turn Dev Mode OFF"
            self.set_background_color("red")
            notify_text = "Developer mode enabled. Services will run in developer mode on next start."
        else:
            self.text = "Turn Dev Mode ON"
            self.set_background_color("blue")
            notify_text = "Developer mode disabled. Services will run in normal mode on next start."
        
        ui.notify(notify_text)

def build_ui() -> None:
    ui.markdown("# LOS! Control Panel")

    ui.separator()

    label = ui.markdown()

    ui.timer(
        interval=1.0,
        callback=lambda: label.set_content(f"*current time: {datetime.now():%X}*"),
    )

    ui.separator()

    with ui.row():
        ui.markdown("##### Services: ")

        ui.markdown("###### Necessary services needed to make LOS! possible :)")

    ui.separator()

    with ui.grid(columns=3):
        for service in SERVICES:
            with ui.column():
                ui.label(service.name)
                ui.label(service.description)
                ServiceButton(service)

    ui.separator()

    with ui.row():
        with ExitButton():
            ui.tooltip("Exit the application and stop all running services")

        DevModeToggle()

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
        for service in SERVICES:
            if service.running:
                service.stop()