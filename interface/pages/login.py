from typing import Callable

from nicegui import ui
from nicegui.elements.textarea import Textarea

import core.usecases.application.authentication as auth_usecases
import core.usecases.domain.profiles as profiles_usecases


class CreateProfileButton(ui.button):
    def __init__(self, profile_input: Textarea, profile_render_function: Callable[[Textarea], None]) -> None:
        super().__init__("Create Profile")

        self.profile_input = profile_input
        self.profile_render_function = profile_render_function

        profile_input.on_value_change(self.on_input_change)

        self.on_click(self.execute)
    
    def on_input_change(self) -> None:
        self.text = f"Create Profile ({self.profile_input.value})"

    def execute(self) -> None:
        profile_name = self.profile_input.value
        
        if not profile_name:
            ui.notify("Please enter a profile name")
            return

        if profiles_usecases.profile_exists(profile_name):
            ui.notify("Profile already exists, please choose a different name")
            return

        profiles_usecases.create_new_profile(profile_name)
        self.profile_render_function.refresh(self.profile_input)
        ui.notify(f"Profile {profile_name} created")


class LoginButton(ui.button):
    def __init__(self, profile_input: Textarea) -> None:
        super().__init__("Login")
        self.profile_input = profile_input
        self.on_click(self.execute)

    def execute(self) -> None:
        profile_name = self.profile_input.value
        
        if not profile_name:
            ui.notify("Please enter a profile name")
            return

        if not profiles_usecases.profile_exists(profile_name):
            ui.notify("Profile does not exist")
            return

        auth_usecases.log_in(profile_name)
        ui.notify(f"Logged in as {profile_name}, you may now login to the osu! client with any username and password!")
        ui.navigate.to("/dashboard")


class DeleteProfileButton(ui.button):
    def __init__(self, profile_input: Textarea, profile_render_function: Callable[[Textarea], None]) -> None:
        super().__init__("Delete Profile")
        self.profile_input = profile_input
        self.profile_render_function = profile_render_function
        self.dialog = None
        profile_input.on_value_change(self.on_input_change)
        self.on_click(self.verify_deletion)

    def on_input_change(self) -> None:
        self.text = f"Delete Profile ({self.profile_input.value})"

    def verify_deletion(self) -> None:
        profile_name = self.profile_input.value
        
        if not profile_name:
            ui.notify("Please enter a profile name")
            return

        if not profiles_usecases.profile_exists(profile_name):
            ui.notify("Profile does not exist")
            return

        with ui.dialog() as dialog, ui.card():
            ui.markdown((
                "Are you sure you want to delete this profile? "
                f"This action cannot be undone & all data associated with the profile **{self.profile_input.value}** will be lost."
            ))
            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Yes", on_click=self.confirm_deletion)
        self.dialog = dialog
        dialog.open()

    def confirm_deletion(self) -> None:
        if self.dialog:
            self.dialog.close()

        profile_name = self.profile_input.value
        profiles_usecases.delete_profile(profile_name)

        self.profile_render_function.refresh(self.profile_input)
        ui.notify(f"Profile {profile_name} deleted")


class ProfileButton(ui.button):
    def __init__(self, profile_name: str, profile_input: Textarea) -> None:
        super().__init__(profile_name)
        self.profile_input = profile_input
        self.on_click(self.execute)
    
    def execute(self) -> None:
        self.profile_input.value = self.text
        ui.notify(f"Selected profile {self.text}")


def build() -> None:
    
    @ui.refreshable
    def build_profiles(profile_input: Textarea) -> None:
        profiles = profiles_usecases.get_all()
        for profile_name, profile in profiles.items():
            if profile.profile_picture is None:
                avatar = "https://a.ppy.sh/"
            else:
                avatar = profile.profile_picture
            with ui.interactive_image(avatar, size=(256, 256)):
                ProfileButton(profile_name, profile_input)

    @ui.page("/login")
    def login() -> None:
        if auth_usecases.is_logged_in():
            ui.navigate.to("/dashboard")
            return
        ui.label("Welcome to LOS!")

        profile_input = ui.textarea("Create Profile: ")

        with ui.row():
            CreateProfileButton(profile_input, build_profiles)
            DeleteProfileButton(profile_input, build_profiles)
            LoginButton(profile_input)

        with ui.row():
            build_profiles(profile_input)
        
        ui.button(
            "Server Settings",
            on_click=lambda: ui.navigate.to("/server-settings")
        )