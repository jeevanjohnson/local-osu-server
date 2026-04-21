from core.usecases.domain.ossapiasync import OssapiAsync
import core.usecases.domain.server_settings as server_settings_usecases

class InvalidOsuApiCredentialsError(Exception):
    pass

def get_api_client() -> OssapiAsync:
    client_id = server_settings_usecases.get_osu_api_v2_client_id()
    client_secret = server_settings_usecases.get_osu_api_v2_client_secret()

    if not client_id or not client_secret:
        raise InvalidOsuApiCredentialsError("Client ID and Client Secret must be set in server settings to use the osu! API.")

    return OssapiAsync(
        client_id=client_id,
        client_secret=client_secret,
    )