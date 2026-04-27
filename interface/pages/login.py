import sys  # noqa
from pathlib import Path  # noqa

sys.path.append(str(Path(__file__).parent.parent))  # noqa

from core.models.adapters.database.profile import Profile
from typing import Callable

from nicegui import ui
from nicegui.elements.dialog import Dialog
from interface.components import BaseButton

from core.usecases.domain.authentication import AuthenticationDomainUseCase
from interface.usecases.domain.profile import ProfileDomainUseCase

AUTHENTICATION_DOMAIN_USECASE = AuthenticationDomainUseCase()
PROFILE_DOMAIN_USECASE = ProfileDomainUseCase()


class CreateProfileSection:
    def __init__(self, rerender_profiles: ui.refreshable) -> None:
        self.rerender_profiles = rerender_profiles

        with ui.row():
            self.new_profile_input = ui.input(
                placeholder="Enter new profile name here"
            ).classes(
                "w-96"
            ).style(
                "background-color: #1c1c1c; color: #ffffff;"
            ).props(
                "outlined"
            )

            self.submit_btn = ui.button(
                "Create Profile",
                on_click=self.create_profile
            ).classes(
                "self-stretch"
            )

    async def create_profile(self) -> None:
        try:
            await PROFILE_DOMAIN_USECASE.create_profile(self.new_profile_input.value)
        except Exception as e:
            ui.notify(e)
            return

        ui.notify(
            f"Profile successfully created: {self.new_profile_input.value}"
        )

        await self.rerender_profiles.refresh()


class ProfileCard:
    def __init__(self, profile_name: str, pfp_url: str) -> None:
        self.profile_name = profile_name
        self.card = ui.card()

        with self.card:
            ui.image(pfp_url)
            ui.label(profile_name)

            with ui.row():
                self.login_btn = ui.button(
                    "Login",
                    on_click=self.login
                )

                self.delete_btn = ui.button(
                    "Delete",
                    on_click=self.delete
                )

        self.dialog: Dialog

    async def login(self):
        await PROFILE_DOMAIN_USECASE.login(
            self.profile_name
        )
        ui.navigate.to("/dashboard")

    async def _delete(self):
        await PROFILE_DOMAIN_USECASE.delete(
            self.profile_name
        )
        self.card.delete()
        self.dialog.close()

    async def delete(self):
        warning_message = (
            f"### Are you sure you want to delete the profile **{self.profile_name}**? "
            "This action cannot be undone!"
        )

        with ui.dialog() as self.dialog, ui.card():
            ui.markdown(warning_message).classes("text-center")

            with ui.column().classes(
                "flex items-center justify-center w-full"
            ):
                with ui.row():
                    ui.button("Cancel", on_click=self.dialog.close)
                    ui.button(
                        "Delete",
                        on_click=self._delete,
                        color="red"
                    )

        self.dialog.open()


def build(template: Callable[[], None]) -> None:

    @ui.refreshable
    async def render_profiles():
        profiles = await PROFILE_DOMAIN_USECASE.get_all()
        with ui.grid(columns=3):
            for profile in profiles:
                ProfileCard(
                    profile.name,
                    profile.avatar_url
                )

    @ui.page("/login")
    async def login() -> None:
        if await AUTHENTICATION_DOMAIN_USECASE.is_logged_in():
            ui.navigate.to("/dashboard")
            return

        template()

        with ui.column().classes(
            "flex items-center "
            "justify-center "
            "w-full "
            "max-w-2xl "
            "mx-auto "
            "min-h-screen "
            "gap-6 "
        ):
            # with ui.column().classes("items-center gap-4"):
            ui.markdown("# Welcome to LOS!")

            ui.button(
                "Server Settings",
                on_click=lambda: ui.navigate.to("/server-settings"),
            )

            ui.separator()

            await render_profiles()

            ui.separator()

            CreateProfileSection(render_profiles)
