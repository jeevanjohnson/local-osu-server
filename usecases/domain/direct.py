import ossapi.models

from models.domain.gameplay import osuGameMode
from osuProtocol.client_web import (
    DirectBeatmap,
    DirectBeatmapSet,
)


async def transform_beatmapset_to_direct(
    beatmap_set: ossapi.models.Beatmapset,
) -> DirectBeatmapSet:
    direct_beatmaps: list[DirectBeatmap] = []
    if beatmap_set.beatmaps is not None:
        for beatmap in beatmap_set.beatmaps:
            direct_beatmaps.append(
                DirectBeatmap(
                    star_rating=beatmap.difficulty_rating,
                    difficulty_name=beatmap.version,
                    cs=beatmap.cs,
                    od=beatmap.accuracy,
                    ar=beatmap.ar,
                    hp=beatmap.drain,
                    mode=osuGameMode.from_api_v2(beatmap.mode),
                )
            )

    return DirectBeatmapSet(
        id=beatmap_set.id,
        artist=beatmap_set.artist,
        title=beatmap_set.title,
        creator=beatmap_set.creator,
        has_video=beatmap_set.video,
        has_story=beatmap_set.storyboard,
        last_updated=beatmap_set.last_updated,
        status=beatmap_set.ranked,
        maps=direct_beatmaps,
    )
