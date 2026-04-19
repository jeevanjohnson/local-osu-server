from nicegui import ui


def build() -> None:
    @ui.page("/")
    def homepage() -> None:
        ui.label("Welcome to the LOS! Interface.")
