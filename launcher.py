import multiprocessing
from datetime import datetime
from typing import Callable

from nicegui import app, ui


class ApplicationService:
    def __init__(
        self,
        name: str,
        description: str,
        launch: Callable[[], None],
        shutdown: Callable[[], None],
    ) -> None:
        self.name = name
        self.description = description
        self.launch = multiprocessing.Process(target=launch)
        self.shutdown = shutdown
        self.running = False

    def start(self) -> None:
        self.launch.start()
        self.running = True

    def stop(self) -> None:
        if self.launch.is_alive():
            self.launch.terminate()
            self.launch.join(timeout=5)
        self.shutdown()
        self.running = False


from proxy.main import run, shutdown

SERVICES: list[ApplicationService] = [
    ApplicationService(
        name="Proxy",
        description="The proxy process which allows the osu! client to connect to the server.",
        launch=run,
        shutdown=shutdown,
    )
    # ApplicationService(
    #     name="Server",
    #     description="The server which the osu! client connects to.",
    #     entrypoint=Path("./server/main.py"),
    # ),
    # ApplicationService(
    #     name="Interface",
    #     description="The user interface for interacting with the application.",
    #     entrypoint=Path("./interface/main.py"),
    # ),
    # ApplicationService(
    #     name="Proxy",
    #     description="The proxy process which allows the osu! client to connect to the server.",
    #     entrypoint=Path("./proxy/main.py"),
    # ),
    # ApplicationService(
    #     name="Watcher",
    #     description="The watcher process monitors the songs folder.",
    #     entrypoint=Path("./watcher/main.py"),
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
        title="Application Control Panel",
        port=5432,
        dark=True,
        frameless=True,
        native=True,
        reload=False,
        show=True,
    )
