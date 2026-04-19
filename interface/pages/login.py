from typing import Callable

from nicegui import ui
from nicegui.elements.dialog import Dialog

import core.usecases.application.authentication as auth_usecases
import core.usecases.domain.profiles as profiles_usecases

class InputStyle(ui.input):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.classes("w-96")
        self.style("background-color: #1c1c1c; color: #ffffff;")
        self.props("outlined")

def render_profiles(on_profile_select: Callable[[str], None], dialog: Dialog | None = None) -> None:
    profiles = profiles_usecases.get_all()

    with ui.grid(columns=5):
        for profile_name, profile in profiles.items():
            if profile.profile_picture is None:
                avatar_url = "https://a.ppy.sh/"
            else:
                avatar_url = profile.profile_picture 

            with ui.column():
                ui.interactive_image(avatar_url, size=(256, 256))
                ui.button(
                    profile_name,
                    on_click=lambda: on_profile_select(profile_name),
                ).classes("w-full").style("word-break: break-word; white-space: normal; overflow-wrap: break-word;")
    
    if dialog is not None:
        ui.button("Cancel", on_click=dialog.close)

class CreateProfileButton(ui.button):
    def __init__(self) -> None:
        super().__init__("Create Profile")

        self.dialog: Dialog | None = None

        self.on_click(self.open_dialog)

    def create_profile(self, profile_name: str) -> None:
        if not profile_name:
            ui.notify("Please enter a profile name")
            return

        if profiles_usecases.profile_exists(profile_name):
            ui.notify("Profile already exists, please choose a different name")
            return

        profiles_usecases.create_new_profile(profile_name)

        if self.dialog is not None:
            self.dialog.close()

        ui.notify(f"Profile {profile_name} created")

    def open_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card():
            profile_name_input = InputStyle("Enter a profile name here!")
            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Create", on_click=lambda: self.create_profile(profile_name_input.value))

        self.dialog = dialog
        dialog.open()

class LoginButton(ui.button):
    def __init__(self) -> None:
        super().__init__("Login")
        self.on_click(self.open_dialog)

    def login(self, profile_name: str) -> None:
        auth_usecases.log_in(profile_name)
        ui.navigate.to("/dashboard")
        msg = f"Logged in as {profile_name}, you may now login to the osu! client!"
        ui.notify(msg)

    def open_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card():
            ui.label("Please select a profile to log in with:")
            render_profiles(self.login, dialog)
        self.dialog = dialog
        dialog.open()

class DeleteProfileButton(ui.button):
    def __init__(self) -> None:
        super().__init__("Delete Profile")
        self.dialog: Dialog | None = None
        self.on_click(self.open_dialog)

    def delete_profile(self, profile_name: str) -> None:
        if not profiles_usecases.profile_exists(profile_name):
            ui.notify("Profile does not exist")
            return

        profiles_usecases.delete_profile(profile_name)

        if self.dialog is not None:
            self.dialog.close()

        ui.notify(f"Profile {profile_name} deleted")

    def open_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card():
            ui.label("Please select a profile to delete:")

            render_profiles(self.delete_profile, dialog)

        self.dialog = dialog
        dialog.open()

def build(template: Callable[[], None]) -> None:
    @ui.page("/login")
    def login() -> None:
        template()

        if auth_usecases.is_logged_in():
            ui.navigate.to("/dashboard")
            return

        with ui.column().classes("flex items-center justify-center w-full min-h-screen gap-6"):

            with ui.column().classes("items-center gap-4"):
                ui.markdown("# Welcome to LOS!")
                ui.separator().classes("w-96")
                LoginButton()
                CreateProfileButton()
                DeleteProfileButton()

            ui.separator().classes("w-96")

            ui.button(
                "Server Settings",
                on_click=lambda: ui.navigate.to("/server-settings")
            )