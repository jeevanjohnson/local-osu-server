"""
Purpose/Domain/Concept:
- This file builds the GUI for the application using NiceGUI.
"""

import os

import emoji
from nicegui import ui
from nicegui.elements.upload_files import FileUpload
from nicegui.events import UploadEventArguments

import usecases.profiles
import usecases.server_settings
import usecases.sessions
from constants import LOS_GUI_PORT
from models.database.profiles import CurrentProfiles as Profiles


def contains_emoji(string: str) -> bool:
    return emoji.emoji_count(string) > 0


def dark_mode():
    dark = ui.dark_mode()
    dark.enable()


# todo: render functions to seperate logic and presentation?


@ui.page("/")
async def login():
    dark_mode()

    ui.label("Welcome to Los!")

    def on_username_change():
        create_profile.set_text(f"Create Profile: '{profile_textarea.value}'")

    profile_textarea = ui.textarea("Selected Profile", on_change=on_username_change)

    @ui.refreshable
    def render_profiles(profiles: Profiles | None):
        if profiles is None:
            ui.label("No profiles found. Please create a new profile.")
            return

        for profile_name, profile in profiles.all.items():

            def on_profile_selection(username=profile_name):
                profile_textarea.set_value(username)

            if profile.profile_picture is None:
                avatar_url = "https://a.ppy.sh/"

            with ui.interactive_image(
                avatar_url, size=(256, 256)
            ):  # .classes('relative'):
                ui.button(profile_name, on_click=on_profile_selection).classes(
                    "absolute bottom-0 left-0 m-2"
                )

    with ui.row():
        profiles = usecases.profiles.get_profiles()
        render_profiles(profiles)

    def on_login_click():
        if not profile_textarea.value:
            ui.notify("Please enter a profile name.")
            return

        profile = usecases.profiles.get_profile(profile_textarea.value)
        if profile is None:
            ui.notify("Profile not found. Please enter a valid profile name.")
            return

        active_session = usecases.sessions.get_current_session()
        if active_session:
            usecases.sessions.delete_current_session()

        usecases.sessions.create_session(profile_textarea.value)

        ui.notify(
            f"Login successful! Profile '{profile_textarea.value}' is now active. Please start the osu! client to use this profile."
        )

        ui.navigate.to("/dashboard")

    with ui.dialog() as dialog, ui.card():
        ui.label(
            (
                "Are you sure you want to delete this profile? "
                "This action cannot be undone & all data will be deleted relative to the profile."
            )
        )
        with ui.row():
            ui.button("Cancel", on_click=dialog.close)
            ui.button(
                "Yes",
                on_click=lambda: [
                    dialog.close(),
                    _on_delete_click(),  # lil cursed, but allows both funcs to be called without doing too much
                ],
            )

    def on_delete_click():
        if not profile_textarea.value:
            ui.notify("Please enter a profile name.")
            return

        dialog.open()

    def _on_delete_click():
        if not profile_textarea.value:
            ui.notify("Please enter a profile name.")
            return

        profile = usecases.profiles.get_profile(profile_textarea.value)
        if profile is None:
            ui.notify("Profile not found. Please enter a valid profile name.")
            return

        usecases.profiles.delete_profile(profile_textarea.value)

        render_profiles.refresh(usecases.profiles.get_profiles())

        profile_textarea.set_value("")

        ui.notify(f"Deleted profile {profile_textarea.value}")

    def on_create_click():
        if not profile_textarea.value:
            ui.notify("Please enter a profile name.")
            return

        profile = usecases.profiles.get_profile(profile_textarea.value)

        if profile is not None:
            ui.notify("Profile already exists. Please choose a different name.")
            return

        if contains_emoji(profile_textarea.value):
            ui.notify("Profile name cannot contain emojis.")
            return

        usecases.profiles.create_profile(profile_textarea.value)

        render_profiles.refresh(usecases.profiles.get_profiles())

        ui.notify(
            (
                f"Profile '{profile_textarea.value}' created successfully! "
                "Please log in to the dashboard before using the osu! client, otherwise it will reject your session."
            )
        )

    with ui.row():
        ui.button("Login", on_click=on_login_click)
        ui.button("Delete Profile", on_click=on_delete_click)
        create_profile = ui.button("Create Profile", on_click=on_create_click)

    ui.button("Server Settings", on_click=lambda: ui.navigate.to("/server_settings"))


@ui.page("/server_settings")
async def server_settings():
    dark_mode()

    ui.label("Server Settings")

    server_settings = usecases.server_settings.get_server_settings()

    if server_settings is None:
        ui.label(
            "No server settings found. This should never happen, please contact the developer."
        )
        return

    def on_setting_change(setting_name: str, setting_value):
        server_settings = usecases.server_settings.get_server_settings()

        if server_settings is None:
            ui.notify(
                "No server settings found. This should never happen, please contact the developer."
            )
            return

        if setting_value == "":
            setting_value = None

        server_settings = server_settings.model_copy(
            update={setting_name: setting_value}
        )
        usecases.server_settings.update_server_settings(server_settings)

        ui.notify(f"Updated setting '{setting_name}' to '{setting_value}'")

    # TODO: PROBABLY SHOULD BE HARDCODED?
    for setting_name, setting_value in server_settings.model_dump().items():
        if setting_name == "model_version":
            continue  # jays-tools specific, not a server setting

        if isinstance(setting_value, bool):
            ui.checkbox(
                setting_name,
                value=setting_value,
                on_change=lambda e, name=setting_name: on_setting_change(name, e.value),
            )
        elif setting_value is None:
            ui.textarea(
                f"{setting_name}",
                value="",
                on_change=lambda e, name=setting_name: on_setting_change(name, e.value),
            )
        else:
            ui.textarea(
                f"{setting_name}",
                value=str(setting_value),
                on_change=lambda e, name=setting_name: on_setting_change(name, e.value),
            )

    ui.button("Previous Page", on_click=ui.navigate.back)


@ui.page("/profile_settings")
async def profile_settings():
    ...

    ui.button("Previous Page", on_click=ui.navigate.back)


@ui.page("/dashboard")
async def dashboard():
    dark_mode()

    session = usecases.sessions.get_current_session()
    if session is None:
        ui.notify("No active session found. Please log in first.")
        ui.navigate.to("/")
        return

    profile_name = session.profile_name

    client_opened: bool = session.osu_client.opened

    def render_if_client_opened():
        nonlocal client_opened

        session = usecases.sessions.get_current_session()
        if session is None:
            ui.notify("No active session found. Please log in first.")
            ui.navigate.to("/")
            return

        if session.osu_client.opened and not client_opened:
            message = "osu! client opened! Dashboard features are now active."

            ui.notify(message)
            client_opened = True
            render_welcome_message.refresh(message)

        elif not session.osu_client.opened and client_opened:
            message = "osu! client closed. Dashboard features are now inactive."

            ui.notify(message)
            client_opened = False
            render_welcome_message.refresh(message)
        else:
            pass  # no change, do nothing

    @ui.refreshable
    def render_welcome_message(message: str | None = None):
        if message is None:
            ui.label(f"Welcome to Los! {profile_name}")
        else:
            ui.label(f"Welcome to Los! {profile_name}, {message}")

    if client_opened:
        render_welcome_message("osu! client opened! Dashboard features are now active.")
    else:
        render_welcome_message(
            "To get started, please open your osu! client shortcut and log in with any credentials."
        )

    ui.timer(2, render_if_client_opened)

    profile = usecases.profiles.get_profile(profile_name)
    if profile is None:
        ui.notify("Profile not found. Please log in again.")
        ui.navigate.to("/")
        return

    if profile.profile_picture is None:
        profile_picture = "https://a.ppy.sh/"

    # profile picture changing
    pfp_file_upload: FileUpload | None = None

    async def _on_change_profile_picture_click():
        dialog.close()
        await on_change_profile_picture_click()

    def on_pfp_upload(upload_event: UploadEventArguments):
        nonlocal pfp_file_upload
        pfp_file_upload = upload_event.file

    with ui.dialog() as dialog, ui.card():
        ui.label("Change Profile Picture Here:")
        profile_picture_input = ui.textarea("Profile Picture URL")
        ui.label("Or Upload Profile Picture below:")
        ui.upload(on_upload=on_pfp_upload, max_file_size=65536)

        ui.button("Confirm", on_click=_on_change_profile_picture_click)

    change_pfp_confirmation = dialog.open

    async def on_change_profile_picture_click():
        nonlocal pfp_file_upload

        profile = usecases.profiles.get_profile(profile_name)
        if profile is None:
            ui.notify("Profile not found. Please log in again.")
            ui.navigate.to("/")
            return

        if profile_picture_input.value:
            profile.profile_picture = profile_picture_input.value
        elif pfp_file_upload is not None:
            file_extension = os.path.splitext(pfp_file_upload.name)[1]
            pfp_location = f"./.data/pfps/{profile_name}{file_extension}"
            await pfp_file_upload.save(pfp_location)
            profile.profile_picture = pfp_location
        else:
            ui.notify(
                "Please provide a profile picture URL or upload a profile picture."
            )
            return

        usecases.profiles.update_profile(profile_name, profile)

        render_profile_picture.refresh(profile.profile_picture)

        ui.notify("Profile picture updated successfully!")

    @ui.refreshable
    def render_profile_picture(profile_picture: str):
        ui.interactive_image(profile_picture, size=(256, 256))

    last_cover_url: str | None = None

    def render_currently_looking_at_if_changed():
        nonlocal last_cover_url

        session = usecases.sessions.get_current_session()
        if session is None:
            cover_url = None
        else:
            if session.latest_beatmap is None:
                cover_url = None
            else:
                cover_url = f"https://assets.ppy.sh/beatmaps/{session.latest_beatmap.set_id}/covers/cover.jpg"

        if cover_url == last_cover_url:
            return

        last_cover_url = cover_url
        currently_looking_at_container.clear()

        with currently_looking_at_container:
            if cover_url is None:
                ui.label("Not currently looking at any beatmap in game.")
            else:
                ui.interactive_image(cover_url)

    with ui.row():
        render_profile_picture(profile_picture)
        with ui.column() as currently_looking_at_container:
            ui.label("Not currently looking at any beatmap in game.")

    render_currently_looking_at_if_changed()
    ui.timer(2, render_currently_looking_at_if_changed)

    ui.button("Change Profile Picture", on_click=change_pfp_confirmation)

    async def on_logout_click():
        usecases.sessions.delete_current_session()
        ui.notify("Logged out successfully!")
        ui.navigate.to("/")

    ui.button("Logout", on_click=on_logout_click)

    def update_notes(new_notes: str):
        profile = usecases.profiles.get_profile(profile_name)
        if profile is None:
            ui.notify("Profile not found. Please log in again.")
            ui.navigate.to("/")
            return

        profile.notes = new_notes

        usecases.profiles.update_profile(profile_name, profile)

        ui.notify("Notes updated successfully!")

    ui.textarea(
        "Notes",
        value=profile.notes if profile.notes is not None else "",
        on_change=lambda e: update_notes(e.value),
    )

    ui.button("Server Settings", on_click=lambda: ui.navigate.to("/server_settings"))


try:
    ui.run(title="LOS GUI", port=LOS_GUI_PORT, show=False, reload=False)
except KeyboardInterrupt:
    pass
