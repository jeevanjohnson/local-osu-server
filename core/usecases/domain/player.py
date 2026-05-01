import core.usecases.domain.client_state as client_state_usecases
import core.usecases.domain.profiles as profiles_usecases
from core.models.application.states.client import ClientState
from core.models.domain.gameplay.game_mode import GameMode
from core.models.adapters.database.profile import Performance, Profile, ProfileSettings
import server.adapters.osu_protocol.cho.server as cho_server


class Player:
    """Minimal player reference with direct access to profile and client state."""

    def __init__(self, name: str) -> None:
        """Initialize player with a profile name."""
        self.name = name

    def get_profile(self) -> Profile:
        """Fetch player profile from repository."""
        profile = profiles_usecases.get(self.name)
        if not profile:
            raise ValueError(f"Profile '{self.name}' not found")
        return profile

    def get_settings(self) -> ProfileSettings:
        """Get player settings from profile."""
        profile = self.get_profile()
        return profile.settings

    def update_settings(self, settings: ProfileSettings) -> ProfileSettings:
        """Update player settings in profile."""
        profile = self.get_profile()
        profile.settings = settings
        updated_profile = self.update_profile(profile)
        return updated_profile.settings

    def get_performance(self, game_mode: GameMode) -> Performance:
        """Get performance stats for a specific game mode."""
        profile = self.get_profile()
        return profile.performance[game_mode]

    def update_performance(
        self, game_mode: GameMode, performance: Performance
    ) -> Performance:
        """Update performance stats for a game mode."""
        profile = self.get_profile()
        profile.performance[game_mode] = performance
        updated_profile = self.update_profile(profile)
        return updated_profile.performance[game_mode]

    def get_client_state(self) -> ClientState:
        """Fetch client state from repository."""
        return client_state_usecases.get_client_state()

    def update_profile(self, profile: Profile) -> Profile:
        """Update profile in repository."""
        return profiles_usecases.update_profile(self.name, profile)

    def update_client_state(self, client_state: ClientState) -> ClientState:
        """Update client state in repository."""
        return client_state_usecases.update_client_state(client_state)

    def extract_outgoing_packets(self) -> bytes:
        """Extract and clear outgoing packets from client state.

        Returns the queued packets, then clears the queue.
        """
        client_state = self.get_client_state()

        outgoing_packets = bytes(client_state.outgoing_packets)
        client_state.outgoing_packets.clear()

        self.update_client_state(client_state)

        return outgoing_packets

    def update_client_stats(self) -> ClientState:
        """Update client state with current profile stats."""
        client_state = self.get_client_state()
        performance = self.get_performance(client_state.game_mode)

        if "SV2" in client_state.mods:
            total_score = performance.total_score_v2
            ranked_score = performance.ranked_score_v2
        else:
            total_score = performance.total_score_v1
            ranked_score = performance.ranked_score_v1

        client_state.outgoing_packets += cho_server.PlayerStats(
            user_id=2,
            action=client_state.status,
            info_text=client_state.status_message,
            beatmap_md5=client_state.beatmap.md5,
            mods=client_state.mods.to_stable_mods(),
            game_mode=client_state.game_mode,
            beatmap_id=client_state.beatmap.id,
            ranked_score=ranked_score,
            accuracy=performance.accuracy,
            play_count=performance.playcount,
            total_score=total_score,
            rank=performance.rank,
            performance_points=performance.performance_points
        )

        return self.update_client_state(client_state)

    def notify(self, message: str) -> None:
        """Send a notification message to the client."""
        client_state = self.get_client_state()
        client_state.outgoing_packets += cho_server.Notification(message=message)
        self.update_client_state(client_state)