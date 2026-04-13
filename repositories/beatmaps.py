from jays_tools import JsonDatabase

# from adapters import log_time
from constants.paths import BEATMAPS
from models.database.beatmaps import CurrentBeatmap as Beatmap
from models.database.beatmaps import CurrentBeatmaps as Beatmaps
from models.database.beatmaps import CurrentBeatmapSet as BeatmapSet


class BeatmapsRepository:
    def __init__(self) -> None:
        self.beatmaps = JsonDatabase(path=BEATMAPS, models=Beatmaps)

    # log
    async def from_md5(self, md5: str) -> Beatmap | None:
        async with self.beatmaps as beatmaps:
            if md5 not in beatmaps.all["by_md5"]:
                return None

            return beatmaps.all["by_md5"][md5]

    async def from_id(self, id: int) -> Beatmap | None:
        async with self.beatmaps as beatmaps:
            if id not in beatmaps.all["by_id"]:
                return None

            return beatmaps.all["by_id"][id]

    async def from_set_id(self, set_id: int) -> BeatmapSet | None:
        async with self.beatmaps as beatmaps:
            if set_id not in beatmaps.all["by_set_id"]:
                return None

            return beatmaps.all["by_set_id"][set_id]

    # log
    async def insert_beatmap(self, bmap: Beatmap) -> None:
        async with self.beatmaps as beatmaps:
            beatmaps.all["by_id"][bmap.id] = bmap
            beatmaps.all["by_md5"][bmap.md5] = bmap

            self.beatmaps.set(beatmaps)

    # log
    async def insert_beatmap_set(self, beatmap_set: BeatmapSet) -> None:
        async with self.beatmaps as beatmaps:
            beatmaps.all["by_set_id"][beatmap_set.id] = beatmap_set

            for beatmap in beatmap_set.maps:
                beatmaps.all["by_id"][beatmap.id] = beatmap
                beatmaps.all["by_md5"][beatmap.md5] = beatmap

            self.beatmaps.set(beatmaps)

    # log
    async def delete_beatmap(self, beatmap: Beatmap) -> None:
        async with self.beatmaps as beatmaps:
            beatmaps.all["by_id"].pop(beatmap.id, None)
            beatmaps.all["by_md5"].pop(beatmap.md5, None)

            # Also remove from beatmapset if present
            existing_set = beatmaps.all["by_set_id"].get(beatmap.set_id)
            if existing_set is not None:
                remaining_maps = [b for b in existing_set.maps if b.md5 != beatmap.md5]
                if remaining_maps:
                    existing_set.maps = remaining_maps
                    beatmaps.all["by_set_id"][beatmap.set_id] = existing_set
                else:
                    beatmaps.all["by_set_id"].pop(beatmap.set_id, None)

            self.beatmaps.set(beatmaps)

    async def search_by_metadata(
        self,
        artist: str,
        title: str,
        difficulty: str,
        profile_name: str,
        excluded_statuses: list | None = None,
    ) -> Beatmap | None:
        """
        Search for a beatmap by artist, title, and difficulty name.

        Args:
            artist: Artist name (partial match, case-insensitive)
            title: Beatmap title (partial match, case-insensitive)
            difficulty: Difficulty name (partial match, case-insensitive)
            profile_name: Profile name for status lookup
            excluded_statuses: List of statuses to exclude from results

        Returns:
            First matching beatmap, or None if not found
        """
        if excluded_statuses is None:
            excluded_statuses = []

        print(
            f"[DEBUG] search_by_metadata: Looking for artist='{artist}', title='{title}', difficulty='{difficulty}', profile='{profile_name}'"
        )

        async with self.beatmaps as beatmaps:
            total_beatmaps = len(beatmaps.all["by_id"])
            print(
                f"[DEBUG] search_by_metadata: Searching through {total_beatmaps} beatmaps in database"
            )

            exact_match = None
            partial_match = None  # Fallback if title doesn't match exactly

            for beatmap_id, bmap in beatmaps.all["by_id"].items():
                # Check metadata matches
                artist_match = artist.lower() in bmap.artist.lower()
                title_match = title.lower() in bmap.title.lower()
                difficulty_match = difficulty.lower() in bmap.difficulty_name.lower()

                # Check status is not excluded
                beatmap_status = bmap.status.get(profile_name)
                is_excluded = beatmap_status in excluded_statuses

                if is_excluded:
                    continue

                if beatmap_status is None:
                    continue

                # Try exact match first (artist+title+difficulty)
                if artist_match and title_match and difficulty_match:
                    print(
                        f"[DEBUG] search_by_metadata: Found EXACT match - id={bmap.id}, artist='{bmap.artist}', title='{bmap.title}', difficulty='{bmap.difficulty_name}'"
                    )
                    exact_match = bmap
                    break  # Best case, stop searching

                # Fallback: artist+difficulty match (title might have variations like "(Rue)")
                if partial_match is None and artist_match and difficulty_match:
                    print(
                        f"[DEBUG] search_by_metadata: Found partial match (artist+difficulty) - id={bmap.id}, artist='{bmap.artist}', title='{bmap.title}', difficulty='{bmap.difficulty_name}'"
                    )
                    partial_match = bmap

        if exact_match:
            print(
                f"[DEBUG] search_by_metadata: Returning EXACT match id={exact_match.id}"
            )
            return exact_match

        if partial_match:
            print(
                f"[DEBUG] search_by_metadata: Returning PARTIAL match (artist+difficulty) id={partial_match.id}"
            )
            return partial_match

        print(f"[DEBUG] search_by_metadata: No matching beatmap found")
        return None
