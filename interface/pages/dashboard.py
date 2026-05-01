import sys  # noqa
from pathlib import Path  # noqa
sys.path.append(str(Path(__file__).parent.parent))  # noqa

from typing import Callable

from core.models.adapters.database.profile import Profile
from nicegui import ui, events
from nicegui.events import UploadEventArguments
from nicegui.elements.upload_files import FileUpload

from core.models.domain.normalizers.country_codes import CountryCode
from core.usecases.domain.authentication import AuthenticationDomainUseCase
from interface.usecases.domain.profile import ProfileDomainUseCase

AUTHENTICATION_DOMAIN_USECASE = AuthenticationDomainUseCase()
PROFILE_DOMAIN_USECASE = ProfileDomainUseCase()

COUNTRY_FLAG_URL = "https://flagcdn.com/w80/{}.png"


class ControlPanel:
    def __init__(self, profile: Profile) -> None:
        ...


class ProfilePictureSection:
    def __init__(self, profile: Profile) -> None:
        self.profile = profile
        self.cached_input: str | FileUpload | None = None

        with ui.column():
            self.pfp = ui.interactive_image(profile.avatar_url, size=(128, 128)).style(
                "width: 128px; height: 128px; object-fit: cover; border-radius: 50%;"
            )
            self.change_pfp_btn = ui.button(
                "Change Profile Picture",
                on_click=self.execute
            ).classes(
                "w-32"
            )

    async def change_pfp(self) -> None:
        if self.cached_input is None:
            ui.notify("No input provided for profile picture update")
            return

        try:
            self.profile = await PROFILE_DOMAIN_USECASE.update_profile_picture(
                self.profile.name, self.cached_input
            )
        except Exception as e:
            ui.notify(f"Error updating profile picture: {e}")
            return

        self.pfp.set_source(self.profile.avatar_url)
        ui.notify("Profile picture updated successfully!")

        self.dialog.close()

    def cache_input(self, value: str | UploadEventArguments) -> None:
        if isinstance(value, str):
            self.cached_input = value
        else:
            self.cached_input = value.file

    def execute(self) -> None:
        with ui.dialog() as self.dialog, ui.card():
            ui.markdown(
                "Enter a direct link to an image, or upload a local file!"
            ).classes(
                "text-center"
            )

            with ui.column().classes("items-center gap-4"):
                self.url_input = ui.input(
                    label="Image URL",
                    placeholder="https://a.ppy.sh/",
                    on_change=lambda: self.cache_input(self.url_input.value)
                )

                self.local_file_input = ui.upload(
                    label="Image Upload",
                    max_files=1,
                    max_file_size=20 * 1024 * 1024,
                    auto_upload=True,
                    on_upload=self.cache_input
                )

                with ui.row():
                    self.submit_btn = ui.button(
                        "Submit",
                        on_click=self.change_pfp
                    )

                    self.cancel_btn = ui.button(
                        "Cancel",
                        on_click=self.dialog.close
                    )

        self.dialog.open()


class ProfileNotesSection:
    def __init__(self, profile: Profile) -> None:
        self.profile = profile
        self.notes_input = ui.textarea(
            label="Notes",
            placeholder="Add some notes to your profile...",
            value=profile.notes,
            on_change=self.update_notes
        ).classes("w-96")

    async def update_notes(self) -> None:
        new_notes = self.notes_input.value
        try:
            self.profile = await PROFILE_DOMAIN_USECASE.update_profile_notes(
                self.profile.name, new_notes
            )
        except Exception as e:
            ui.notify(f"Error updating profile notes: {e}")


class CountryFlagSection:
    def __init__(self, profile: Profile) -> None:
        self.profile = profile

        self.current_flag = ui.interactive_image(
            COUNTRY_FLAG_URL.format(profile.country_code.name.lower()),
            on_mouse=self.change_country_dialog
        ).style(
            "width: 24px; "
            "height: 16px; "
            "object-fit: cover; "
            "border: 1px solid white; "
            "cursor: pointer; "
            "margin-top: 12px; "
        )

    async def change_country(self, country_code: CountryCode) -> None:
        try:
            self.profile = await PROFILE_DOMAIN_USECASE.update_profile_country(
                self.profile.name, country_code
            )
        except Exception as e:
            ui.notify(f"Error updating country: {e}")
            return

        self.current_flag.set_source(
            COUNTRY_FLAG_URL.format(country_code.name.lower())
        )
        ui.notify("Country updated successfully!")

        self.dialog.close()

    def change_country_dialog(self, event: events.MouseEventArguments) -> None:
        with ui.dialog() as self.dialog, ui.card():
            ui.markdown("### Select your country").classes("text-center")
            with ui.grid(columns=5):
                for code in CountryCode:
                    if code == CountryCode.XX:
                        continue

                    ui.interactive_image(
                        COUNTRY_FLAG_URL.format(code.name.lower()),
                        on_mouse=(
                            lambda event, code=code:
                                self.change_country(code)
                        )
                    ).style(
                        "width: 80px; height: 60px; object-fit: cover; border-radius: 8px; cursor: pointer;"
                    )

            ui.button("Cancel", on_click=self.dialog.close)

        self.dialog.open()


class SideBar:
    def __init__(self, profile: Profile) -> None:

        with ui.row().classes("text-center gap-2"):
            self.name = ui.markdown(f"Logged in as **{profile.name}**")
            CountryFlagSection(profile)

        ProfilePictureSection(profile)

        self.logout_btn = ui.button(
            "Logout",
            on_click=self.logout
        ).classes(
            "w-32"
        )

        self.server_settings_btn = ui.button(
            "Server Settings",
            on_click=lambda: ui.navigate.to("/server-settings"),
        ).classes(
            "w-32"
        )

    async def logout(self) -> None:
        await AUTHENTICATION_DOMAIN_USECASE.logout()
        ui.notify("Logged out successfully")
        ui.navigate.to("/login")


def build(template: Callable[[], None]) -> None:

    @ui.page("/dashboard")
    async def dashboard() -> None:
        if not await AUTHENTICATION_DOMAIN_USECASE.is_logged_in():
            ui.navigate.to("/login")
            return

        profile = await AUTHENTICATION_DOMAIN_USECASE.logged_in_as()
        if profile is None:
            ui.notify("No profile found, please log in again.")
            await AUTHENTICATION_DOMAIN_USECASE.logout()
            ui.navigate.to("/login")
            return

        template()

        with ui.column():
            SideBar(profile)

        ui.separator().props('vertical')

        with ui.column():
            ControlPanel(profile)
