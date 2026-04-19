from nicegui import ui


class BaseButton(ui.button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.props("no-caps")