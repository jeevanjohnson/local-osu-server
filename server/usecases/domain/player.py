from jays_tools.architecture import DomainUseCase
from core.models.adapters.database.client_state import ClientState
from core.models.adapters.database.profile import Profile
from core.models.domain.normalizers.game_mode import GameMode
from core.models.domain.normalizers.mods import Mods
from core.usecases.domain.profiles import ProfilesDomainUseCase
from core.usecases.domain.client_state import ClientStateDomainUseCase
from datetime import datetime
from server.adapters.osu_protocol.cho.packets.packets import ServerPacket, ServerPacketStream
from server.adapters.osu_protocol.cho.packets.packets import friend_list, notify
from server.adapters.osu_protocol.cho.packets.enums import ClientStatus
from core.models.domain.normalizers.client_status import ClientStatus as DomainClientStatus
from core.models.domain.normalizers.scoring_type import ScoringType
from core.usecases.domain.profile_settings import ProfileSettingsDomainUseCase


class PlayerCoreDomainUsecases:
    profile = ProfilesDomainUseCase()
    client_state = ClientStateDomainUseCase()
    profile_settings = ProfileSettingsDomainUseCase()


class PlayerDomainUseCase(DomainUseCase):
    def __init__(self) -> None:
        self.repositories = None
        self.services = None
        self.adapters = None
        self.core_domain_usecases = PlayerCoreDomainUsecases()

    async def update_profile(self, profile: Profile) -> None:
        await self.core_domain_usecases.profile.update_profile(profile)

    async def update_client_state(self, client_state: ClientState) -> None:
        await self.core_domain_usecases.client_state.update_client_state(client_state)

    async def get_current_client_state(self) -> ClientState | None:
        return await self.core_domain_usecases.client_state.get_client_state()

    async def get_current_profile(self) -> Profile | None:
        client_state = await self.core_domain_usecases.client_state.get_client_state()
        if client_state is None:
            return None

        return await self.core_domain_usecases.profile.get(client_state.profile_name)

    async def retrive_current_user_avatar(self) -> str:
        client_state = await self.core_domain_usecases.client_state.get_client_state()
        if client_state is None:
            return "https://a.ppy.sh/"

        current_user_profile = await self.core_domain_usecases.profile.get(client_state.profile_name)
        if current_user_profile is None:
            return "https://a.ppy.sh/"

        return current_user_profile.avatar_url

    async def append_outgoing_packet(self, packets: ServerPacket | ServerPacketStream) -> None:
        client_state = await self.core_domain_usecases.client_state.get_client_state()
        if client_state is None:
            return

        client_state.outgoing_packets += packets
        await self.core_domain_usecases.client_state.update_client_state(client_state)

    async def clear_outgoing_packets(self) -> bytes:
        client_state = await self.core_domain_usecases.client_state.get_client_state()
        if client_state is None:
            return b""

        outgoing_packets = bytes(client_state.outgoing_packets)
        client_state.outgoing_packets.clear()
        await self.core_domain_usecases.client_state.update_client_state(client_state)

        return outgoing_packets

    async def valid_logout(self) -> bool:
        client_state = await self.core_domain_usecases.client_state.get_client_state()
        if client_state is None:
            return False

        if (client_state.logged_in_at.timestamp() - datetime.now().timestamp()) < 1:
            return False

        return True

    async def logout(self) -> None:
        await self.core_domain_usecases.client_state.delete_client_state()

    async def remove_friend(self, friend_id: int) -> None:
        profile = await self.get_current_profile()
        if profile is None:
            return

        if friend_id in profile.friend_ids:
            profile.friend_ids.remove(friend_id)
            await self.update_profile(profile)

        await self.append_outgoing_packet(
            friend_list(profile.friend_ids)
        )

        # TODO: Logout packet?

    async def notify(self, message: str) -> None:
        await self.append_outgoing_packet(
            notify(message)
        )

    async def get_seasonal_backgrounds(self) -> list[str]:
        profile = await self.get_current_profile()
        if profile is None:
            return []

        return profile.seasonal_backgrounds

    async def clear_direct_reference(self) -> None:
        client_state = await self.core_domain_usecases.client_state.get_client_state()
        if client_state is None:
            return

        client_state.direct_cursor_string = None
        client_state.direct_last_query = []
        await self.core_domain_usecases.client_state.update_client_state(client_state)

    async def update_status(self, status: ClientStatus, status_message: str) -> None:
        client_state = await self.core_domain_usecases.client_state.get_client_state()
        if client_state is None:
            return

        client_state.status = DomainClientStatus(status)
        client_state.status_message = status_message
        await self.core_domain_usecases.client_state.update_client_state(client_state)

    async def apply_ruleset(self, mode: GameMode, mods: Mods) -> None:
        profile = await self.get_current_profile()
        if profile is None:
            return

        profile_settings = await self.core_domain_usecases.profile_settings.get_profile_settings(
            profile.name
        )
        if profile_settings is None:
            return

        client_state = await self.core_domain_usecases.client_state.get_client_state()
        if client_state is None:
            return

        client_state.game_mode = mode
        client_state.mods = mods

        if profile_settings.pp_leaderboards:
            client_state.current_scoring_mode = ScoringType.PP
        elif profile_settings.allow_score_v2_submission and "SV2" in mods:
            client_state.current_scoring_mode = ScoringType.SCOREV2
        else:
            client_state.current_scoring_mode = ScoringType.SCOREV1

        if not profile_settings.allow_auto_pilot_submission and "AP" in mods:
            await self.notify(
                "Your profile settings do not allow Auto Pilot submission."
            )

        if not profile_settings.allow_score_v2_submission and "SV2" in mods:
            await self.notify(
                "Your profile settings do not allow ScoreV2 submission."
            )

        if not profile_settings.allow_relax_submission and "RX" in mods:
            await self.notify(
                "Your profile settings do not allow Relax submission."
            )

        if profile_settings.force_nf and "NF" not in mods:
            await self.notify(
                "Your profile settings require NF mod to be applied."
            )

        if profile_settings.force_score_v2 and "SV2" not in mods:
            await self.notify(
                "Your profile settings require ScoreV2 mod to be applied."
            )

        await self.core_domain_usecases.client_state.update_client_state(client_state)
