from jays_tools import JsonDatabase

from constants.paths import CLIENT_UPDATES
from models.database.client.update import ClientUpdate
from osu_protocol.cho.server import Packet, Packets


class ClientUpdateRepository:
    def __init__(self):
        self.client_updates = JsonDatabase(path=CLIENT_UPDATES, models=ClientUpdate)

    async def queue(self, packet: Packet | Packets) -> None:
        async with self.client_updates as client_updates:
            print(f"DEBUG queue: Before adding - {len(client_updates.packets)} bytes")
            client_updates.packets += packet
            print(f"DEBUG queue: After adding - {len(client_updates.packets)} bytes")
            self.client_updates.set(client_updates)

    async def clear(self) -> bytes:
        async with self.client_updates as client_updates:
            print(
                f"DEBUG: Before clear - packets in queue: {len(client_updates.packets)} bytes"
            )
            result = bytes(client_updates.packets)
            client_updates.packets.clear()
            self.client_updates.set(client_updates)
            print(f"DEBUG: After clear - packets set to empty")
            print(f"DEBUG: Returning {len(result)} bytes from clear()")

        return result
