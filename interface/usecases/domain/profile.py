from core.models.domain.normalizers.country_codes import CountryCode
from interface.adapters.catbox import CatboxAdapter
from interface.adapters.image_validation import ImageValidationAdapter
from jays_tools.architecture import DomainUseCase, Adapters
from nicegui.elements.upload_files import FileUpload
from typing import TypeAlias
from core.usecases.domain.profiles import ProfilesDomainUseCase
from core.usecases.domain.authentication import AuthenticationDomainUseCase
from core.models.adapters.database.profile import Profile

URL: TypeAlias = str


class ProfileCoreDomainUsecases:
    profile = ProfilesDomainUseCase()
    auth = AuthenticationDomainUseCase()


class ProfileAdapters(Adapters):
    catbox = CatboxAdapter()
    image_validation = ImageValidationAdapter()


class ProfileDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.adapters = ProfileAdapters()
        self.repositories = None
        self.services = None
        self.core_domain_usecases = ProfileCoreDomainUsecases()

    async def create_profile(self, profile_name: str) -> None:
        if not profile_name:
            raise Exception("need a valid profile name")

        if await self.exists(profile_name):
            raise Exception("profile already exists")

        await self.core_domain_usecases.profile.create_new_profile(profile_name)

    async def exists(self, profile_name: str) -> bool:
        return await self.core_domain_usecases.profile.profile_exists(profile_name)

    async def delete(self, profile_name: str) -> None:
        await self.core_domain_usecases.profile.delete_profile(profile_name)

    async def logout(self) -> None:
        await self.core_domain_usecases.auth.logout()

    async def login(self, profile_name: str) -> None:
        await self.core_domain_usecases.auth.login(profile_name)

    async def get_all(self) -> list[Profile]:
        return await self.core_domain_usecases.profile.get_all()

    async def update_profile_picture_from_url(self, profile_name: str, url: URL) -> Profile:
        if not self.adapters.image_validation.valid_image_from_url(url):
            raise ValueError("Invalid image URL")

        catbox_url = self.adapters.catbox.upload(url)

        return await self.core_domain_usecases.profile.update_pfp(
            profile_name,
            catbox_url
        )

    async def update_profile_picture_from_file(self, profile_name: str, file: FileUpload) -> Profile:
        if not self.adapters.image_validation.valid_image_from_nice_gui_upload(file):
            raise ValueError("Invalid Image Upload")

        catbox_url = await self.adapters.catbox.from_nice_gui_file_upload(file)

        return await self.core_domain_usecases.profile.update_pfp(
            profile_name,
            catbox_url
        )

    async def update_profile_picture(self, profile_name: str, file_or_url: URL | FileUpload) -> Profile:
        if isinstance(file_or_url, str):
            return await self.update_profile_picture_from_url(profile_name, file_or_url)
        else:
            return await self.update_profile_picture_from_file(profile_name, file_or_url)

    async def update_profile_notes(self, profile_name: str, notes: str) -> Profile:
        return await self.core_domain_usecases.profile.update_notes(profile_name, notes)

    async def update_profile_country(self, profile_name: str, country_code: CountryCode) -> Profile:
        return await self.core_domain_usecases.profile.update_country(profile_name, country_code)
