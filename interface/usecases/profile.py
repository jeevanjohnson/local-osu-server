from interface.adapters.catbox import CatboxAdapter
from interface.adapters.image_validation import ImageValidationAdapter
from jays_tools.architecture import DomainUseCase, Adapters
from nicegui.elements.upload_files import FileUpload
from typing import TypeAlias
from core.usecases.domain.profiles import ProfilesDomainUseCase

URL: TypeAlias = str


class ProfileCoreDomainUsecases:
    profile = ProfilesDomainUseCase()


class ProfileAdapters(Adapters):
    catbox = CatboxAdapter()
    image_validation = ImageValidationAdapter()


class ProfileDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.adapters = ProfileAdapters()
        self.repositories = None
        self.services = None
        self.core_domain_usecases = ProfileCoreDomainUsecases()

    async def update_profile_picture_from_url(self, profile_name: str, url: URL) -> None:
        if not self.adapters.image_validation.valid_image_from_url(url):
            raise ValueError("Invalid image URL")

        catbox_url = self.adapters.catbox.upload(url)

        await self.core_domain_usecases.profile.update_pfp(
            profile_name,
            catbox_url
        )

    async def update_profile_picture_from_file(self, profile_name: str, file: FileUpload) -> None:
        if not self.adapters.image_validation.valid_image_from_nice_gui_upload(file):
            raise ValueError("Invalid Image Upload")

        catbox_url = await self.adapters.catbox.from_nice_gui_file_upload(file)

        await self.core_domain_usecases.profile.update_pfp(
            profile_name,
            catbox_url
        )

    async def update_profile_picture(self, profile_name: str, file_or_url: URL | FileUpload) -> None:
        if isinstance(file_or_url, str):
            await self.update_profile_picture_from_url(profile_name, file_or_url)
        else:
            await self.update_profile_picture_from_file(profile_name, file_or_url)
