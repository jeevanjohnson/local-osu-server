import os
import tempfile
from typing import Any, Callable

import requests
import interface.usecases.adapters.catbox as catbox_adapter
from nicegui import ui, events
from nicegui.elements.dialog import Dialog
from nicegui.events import UploadEventArguments

from core.osu_protocol.domain.enums import osuCountryCode
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
        self.render_upload_option: Any = None
        self.on_click(self.execute)

    async def update_pfp_from_path(self, path: UploadEventArguments) -> None:
        ui.notify("Uploading file, please wait...")

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

        try:
            file_url = catbox_adapter.file_upload(temp_path)
        except Exception as e:
            ui.notify(f"Error uploading file: {str(e)}\nPlease use the URL upload option instead or try again later.")
            return
        finally:
            os.remove(temp_path)

        self.update_pfp_from_url(file_url, from_upload=True)
        ui.notify("File uploaded successfully!")

    def is_valid_image_url(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            content_type = response.headers.get("content-type", "")
            return content_type.startswith("image/")
        except Exception:
            return False

    def update_pfp_from_url(self, url: str, from_upload: bool = False) -> None:
        if not from_upload:
            if not self.is_valid_image_url(url):
                ui.notify("Please enter a valid image URL")
                return

        profile = profiles_usecases.get(self.profile_name)
        if profile is None:
            ui.notify("Profile not found")
            return

        profile.avatar_url = url
        profiles_usecases.update_profile(self.profile_name, profile)

        if self.dialog is not None:
            self.dialog.close()

        ui.notify("Profile picture updated successfully!")
        self.refresh_callback(self.profile_name)

        if self.render_upload_option is not None:
            self.render_upload_option.refresh()

    def execute(self) -> None:
        with ui.dialog() as dialog, ui.card():
            with ui.column().classes(
                "flex items-center justify-center w-full"
            ):

                msg = "### Either enter a direct link to an image, or a local file!"
                ui.markdown(msg).classes("text-center")

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

class ChangeCountryFlag(ui.interactive_image):
    def __init__(self, profile_name: str, country_code: osuCountryCode, dialog: Dialog, refresh_flag: Callable[[], None]) -> None:
        flag_url = f"https://flagcdn.com/w80/{country_code.name.lower()}.png"

        super().__init__(flag_url, on_mouse=self.change_flag)
        self.profile_name = profile_name
        self.country_code = country_code
        self.dialog = dialog
        self.refresh_flag = refresh_flag
    
    def change_flag(self) -> None:
        profile = profiles_usecases.get(self.profile_name)
        if profile is None:
            ui.notify("Profile not found")
            return
        
        profile.country_code = self.country_code
        profiles_usecases.update_profile(self.profile_name, profile)

        self.refresh_flag()
        self.dialog.close()

        ui.notify(f"Country changed to {self.country_code.name}")

class CountryFlag(ui.interactive_image):
    def __init__(self, profile_name: str) -> None:
        super().__init__(f"https://flagcdn.com/w80/xx.png", on_mouse=self.open_dialog)
        self.profile_name = profile_name
        self.dialog: Dialog | None = None
        self.refresh()
    
    def refresh(self) -> None:
        profile = profiles_usecases.get(self.profile_name)
        if profile is None:
            ui.notify("Profile not found")
            return
        
        country_code = profile.country_code.name.lower()
        self.set_source(f"https://flagcdn.com/w80/{country_code}.png")

    def change_flag(self, country_code: str) -> None:
        profile = profiles_usecases.get(self.profile_name)
        if profile is None:
            ui.notify("Profile not found")
            return
        
        profile.country_code = osuCountryCode[country_code.upper()]
        profiles_usecases.update_profile(self.profile_name, profile)

        self.refresh()

    def open_dialog(self, event: events.MouseEventArguments) -> None:
        with ui.dialog() as dialog, ui.card():
            ui.markdown("### Select your country").classes("text-center")
            with ui.grid(columns=5):
                for code in osuCountryCode:
                    if code == osuCountryCode.XX:
                        continue
                    
                    ChangeCountryFlag(self.profile_name, code, dialog, self.refresh).style(
                        "width: 80px; height: 60px; object-fit: cover; border-radius: 8px; cursor: pointer;"
                    )
            
            ui.button("Cancel", on_click=dialog.close)
        
        self.dialog = dialog
        dialog.open()

class ProfileNotes(ui.textarea):
    def __init__(self, profile_name: str) -> None:
        super().__init__(label="Notes", placeholder="Add some notes to your profile...")
        self.profile_name = profile_name
        self.classes("w-96")
        self.refresh()

        self.on_value_change(self.on_change)

    def refresh(self) -> None:
        profile = profiles_usecases.get(self.profile_name)
        if profile is None:
            ui.notify("Profile not found")
            return
        
        self.value = profile.notes

    def on_change(self) -> None:
        profile = profiles_usecases.get(self.profile_name)
        if profile is None:
            ui.notify("Profile not found")
            return
        
        profile.notes = self.value
        profiles_usecases.update_profile(self.profile_name, profile)

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
            CountryFlag(profile_name)
    
            ui.separator().classes("w-96")

            with ui.row():
                ChangeProfilePictureButton(
                    profile_name, render_profile_picture.refresh
                )
            
            ProfileNotes(profile_name)

            ui.separator().classes("w-96")

            with ui.row():
                ui.button(
                    "Server Settings",
                    on_click=lambda: ui.navigate.to("/server-settings"),
                )
                LogoutButton()