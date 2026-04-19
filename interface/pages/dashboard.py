import os
import tempfile
from typing import Any, Callable

import requests
from catboxpy.catbox import CatboxClient
from nicegui import ui
from nicegui.elements.dialog import Dialog
from nicegui.events import UploadEventArguments

import core.usecases.application.authentication as auth_usecases
import core.usecases.domain.profiles as profiles_usecases
from interface.components import BaseButton


class LogoutButton(BaseButton):
    def __init__(self) -> None:
        super().__init__("Logout")
        self.on_click(self.execute)

    def execute(self) -> None:
        auth_usecases.log_out()
        ui.notify("Logged out successfully")
        ui.navigate.to("/login")


class ChangeProfilePictureButton(BaseButton):
    def __init__(self, profile_name: str, refresh_callback: Callable[[str], Any]) -> None:
        super().__init__("Change Profile Picture")
        self.dialog: Dialog | None = None
        self.profile_name = profile_name
        self.refresh_callback = refresh_callback
        self.catbox_client = CatboxClient()
        self.render_upload_option: Any = None
        self.on_click(self.execute)

    async def update_pfp_from_path(self, path: UploadEventArguments) -> None:
        file = path.file

        if not file.content_type.startswith("image/"):
            ui.notify("Please upload a valid image file")
            return

        suffix = file.content_type.removeprefix("image/")

        if suffix not in ["png", "jpeg", "jpg", "gif"]:
            msg = "Unsupported image format. Please upload a PNG, JPEG, JPG, or GIF file."
            ui.notify(msg)
            return

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{suffix}"
        ) as temp_file:
            temp_path = temp_file.name
            await file.save(temp_path)

        file_url = self.catbox_client.file_upload(temp_path)
        self.update_pfp_from_url(file_url, from_upload=True)
        os.remove(temp_path)
        ui.notify("File uploaded successfully!")

    def is_valid_image_url(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            content_type = response.headers.get("content-type", "")
            return content_type.startswith("image/")
        except Exception:
            return False

    def update_pfp_from_url(self, url: str, from_upload: bool = False) -> None:
        if not from_upload and not self.is_valid_image_url(url):
            ui.notify("Please enter a valid image URL")
            return

        profiles_usecases.update_avatar_url(self.profile_name, url)

        if self.dialog is not None:
            self.dialog.close()

        ui.notify("Profile picture updated successfully!")
        self.refresh_callback(self.profile_name)

        if self.render_upload_option is not None:
            self.render_upload_option.refresh()

    def execute(self) -> None:
        with ui.dialog() as dialog, ui.card():
            msg = "### Either enter a direct link to an image, or a local file!"
            ui.markdown(msg)

            url_input = ui.input(
                label="Image URL", placeholder="https://a.ppy.sh/"
            )

            ui.button(
                "Use URL", on_click=lambda: self.update_pfp_from_url(url_input.value)
            )

            ui.separator()

            @ui.refreshable
            def render_upload_option() -> None:
                ui.upload(
                    label="Image Upload",
                    max_files=1,
                    auto_upload=True,
                    on_upload=self.update_pfp_from_path,
                    max_file_size=20 * 1024 * 1024,
                )

            self.render_upload_option = render_upload_option
            self.render_upload_option()
            ui.button("Cancel", on_click=dialog.close)

        self.dialog = dialog
        dialog.open()


def build(template: Callable[[], None]) -> None:
    @ui.refreshable
    def render_profile_picture(profile_name: str) -> None:
        profile = profiles_usecases.get(profile_name)
        profile_url = (
            profile.avatar_url
            if profile is not None
            else "https://a.ppy.sh/"
        )
        ui.interactive_image(profile_url, size=(256, 256)).style(
            "width: 256px; height: 256px; object-fit: cover; border-radius: 50%;"
        )

    @ui.page("/dashboard")
    def dashboard() -> None:
        if not auth_usecases.is_logged_in():
            ui.navigate.to("/login")
            return

        result = auth_usecases.current_logged_in_profile()
        if result is None:
            ui.notify("No profile found, please log in again.")
            auth_usecases.log_out()
            ui.navigate.to("/login")
            return

        profile_name, profile = result
        template()

        with ui.column().classes(
            "flex items-center justify-center w-full min-h-screen gap-6"
        ):
            ui.markdown(f"# Welcome `{profile_name}` !!")
            render_profile_picture(profile_name)
            ui.separator().classes("w-96")

            with ui.row():
                ChangeProfilePictureButton(
                    profile_name, render_profile_picture.refresh
                )

            ui.separator().classes("w-96")

            with ui.row():
                ui.button(
                    "Server Settings",
                    on_click=lambda: ui.navigate.to("/server-settings"),
                )
                LogoutButton()