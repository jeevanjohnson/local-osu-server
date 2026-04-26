from jays_tools.architecture import Repository
from core.repositories.database import SQLDatabaseInstance
from core.models.adapters.database.snapshots import SnapShot as AdapterSnapShot

class OsuSnapshotRepository(Repository):
    def __init__(self):
        self.database = SQLDatabaseInstance()
    
    async def save_snapshot(self, domain_snapshot: AdapterSnapShot) -> AdapterSnapShot:
        return await self.database.insert(domain_snapshot)

    async def get_latest_snapshot(self) -> AdapterSnapShot | None:
        adapter_snap_shots = await self.database.find(AdapterSnapShot)
        if not adapter_snap_shots:
            return None

        latest_adapter_snapshot = max(adapter_snap_shots, key=lambda s: s.created_at)
        return latest_adapter_snapshot

    async def create_snapshot(self) -> AdapterSnapShot:
        return await self.database.insert(AdapterSnapShot())