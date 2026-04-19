import multiprocessing
from datetime import datetime
from typing import Any, Callable

from nicegui import app, ui

import osu_watcher.main as osu_watcher
import proxy.main as proxy
import interface.main as interface


class ApplicationService:
    def __init__(
        self,
        name: str,
        description: str,
        service_start: Callable[[], Any],
        service_stop: Callable[[], Any]
    ) -> None:
        self.name = name
        self.description = description
        self.service_start = service_start
        self.service_stop = service_stop
        self.running = False
        self.process: multiprocessing.Process | None = None

    def get_launch_process(self) -> multiprocessing.Process:
        if self.process is None:
            self.process = multiprocessing.Process(target=self.service_start)

        return self.process

    def start(self) -> None:
        process = self.get_launch_process()
        process.start()
        self.running = True

    def stop(self) -> None:
        process = self.get_launch_process()
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)

        self.process = None
        self.service_stop()
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
        name="Interface",
        description="The user interface for interacting with the application.",
        service_start=interface.start,
        service_stop=interface.stop,
    ),
    # ApplicationService(
    #     name="Server",
    #     description="The server which the osu! client connects to.",
    #     entrypoint=Path("./server/main.py"),
    # ),
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

    with ui.grid(columns=len(SERVICES)):
        for service in SERVICES:
            with ui.column():
                ui.label(service.name)
                ui.label(service.description)
                ServiceButton(service)

    ui.separator()

    with ExitButton():
        ui.tooltip("Exit the application and stop all running services")

if __name__ in {
    "__main__",
    "__mp_main__",  # multiprocessing compatibility
}:
    build_ui()
    ui.run(
        title="LOS! Control Panel",
        dark=True,
        frameless=True,
        native=True,
        reload=False,
        show=True,
    )
