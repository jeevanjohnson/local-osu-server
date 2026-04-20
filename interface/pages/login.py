from typing import Callable

from nicegui import ui
from nicegui.elements.dialog import Dialog

import core.usecases.application.authentication as auth_usecases
import core.usecases.domain.profiles as profiles_usecases
from interface.components import BaseButton

class InputStyle(ui.input):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.classes("w-96")
        self.style("background-color: #1c1c1c; color: #ffffff;")
        self.props("outlined")

class ProfileSelectButton(BaseButton):
    def __init__(self, profile_name: str, on_select: Callable[[str], None]) -> None:
        super().__init__(profile_name)
        self.profile_name = profile_name
        self.on_select = on_select
        self.classes("w-full").style(
            "word-break: break-word; white-space: normal; overflow-wrap: break-word;"
        )
        self.on_click(self.execute)

    def execute(self) -> None:
        self.on_select(self.profile_name)

def render_profiles_in_dialog(
    on_profile_select: Callable[[str], None]
) -> None:
    profiles = profiles_usecases.get_all()

    with ui.grid(columns=5):
        for profile_name, profile in profiles.items():
            with ui.column():
                ui.interactive_image(profile.avatar_url, size=(256, 256))
                ProfileSelectButton(profile_name, on_profile_select)


class CreateProfileButton(BaseButton):
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
                ui.button(
                    "Create",
                    on_click=lambda: self.create_profile(profile_name_input.value),
                )
        self.dialog = dialog
        dialog.open()


class LoginButton(BaseButton):
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
            render_profiles_in_dialog(self.login)
            ui.button("Cancel", on_click=dialog.close)
        self.dialog = dialog
        dialog.open()

class DeleteProfileButton(BaseButton):
    def __init__(self) -> None:
        super().__init__("Delete Profile")
        self.first_dialog: Dialog | None = None
        self.second_dialog: Dialog | None = None
        self.on_click(self.open_dialog)
    
    def confirm_delete(self, profile_name: str) -> None:
        with ui.dialog() as dialog, ui.card():
            ui.markdown(f"### Are you sure you want to delete the profile **{profile_name}**? This action cannot be undone!").classes(
                "text-center"
            )
            with ui.column().classes(
                "flex items-center justify-center w-full"
            ):
                with ui.row():
                    ui.button("Cancel", on_click=dialog.close)
                    ui.button(
                        "Delete",
                        on_click=lambda: self.delete_profile(profile_name),
                        color="red"
                    )
                
        self.second_dialog = dialog
        dialog.open()

    def delete_profile(self, profile_name: str) -> None:
        if not profiles_usecases.profile_exists(profile_name):
            ui.notify("Profile does not exist")
            return
        
        profiles_usecases.delete_profile(profile_name)
        
        if self.second_dialog is not None:
            self.second_dialog.close()
        if self.first_dialog is not None:
            self.first_dialog.close()
        
        ui.notify(f"Profile {profile_name} deleted")

    def open_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card():
            ui.label("Please select a profile to delete:")
            render_profiles_in_dialog(self.confirm_delete)
            ui.button("Cancel", on_click=dialog.close)
        
        self.first_dialog = dialog
        dialog.open()

def build(template: Callable[[], None]) -> None:
    @ui.page("/login")
    def login() -> None:
        template()
        if auth_usecases.is_logged_in():
            ui.navigate.to("/dashboard")
            return
        with ui.column().classes(
            "flex items-center justify-center w-full min-h-screen gap-6"
        ):
            with ui.column().classes("items-center gap-4"):
                ui.markdown("# Welcome to LOS!")
                ui.separator().classes("w-96")
                LoginButton()
                CreateProfileButton()
                DeleteProfileButton()
            
            ui.separator().classes("w-96")
            ui.button(
                "Server Settings",
                on_click=lambda: ui.navigate.to("/server-settings"),
            )