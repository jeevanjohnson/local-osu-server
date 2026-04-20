import core.usecases.domain.client_state as client_state_usecases
import core.usecases.domain.profiles as profiles_usecases
from core.models.application.states.client import ClientState
from core.models.domain.gameplay import GameMode
from core.models.profile import Performance, Profile


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

    def get_performance(self, game_mode: GameMode) -> Performance:
        """Get performance stats for a specific game mode."""
        profile = self.get_profile()
        return profile.performance[game_mode]

    def update_performance(
        self, game_mode: GameMode, performance: Performance
    ) -> None:
        """Update performance stats for a game mode."""
        profile = self.get_profile()
        profile.performance[game_mode] = performance
        self.update_profile(profile)

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