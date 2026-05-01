from core.adapters.osuapi import OssapiAsync
from jays_tools.architecture import DomainUseCase, Adapters


class OsuApiV2Adapters(Adapters):
    ossapi_async_client = OssapiAsync


class OsuApiV2DomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.adapters = OsuApiV2Adapters()
        self.repositories = None
        self.services = None

    async def get_api_client(self, client_id: int, client_secret: str) -> OssapiAsync:
        if not client_id or not client_secret:
            raise Exception(
                "Client ID and Client Secret must be set in server settings to use the osu! API.")

        return self.adapters.ossapi_async_client(
            client_id=client_id,
            client_secret=client_secret,
        )
