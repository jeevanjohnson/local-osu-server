from enum import IntEnum, unique


@unique
class BeatmapSetStatus(IntEnum):
    """
    Represents the ranked status of a beatmap.
    """

    NOT_SUBMITTED = -1
    PENDING = 0
    UPDATE_AVAILABLE = 1
    RANKED = 2
    APPROVED = 3
    QUALIFIED = 4
    LOVED = 5

    @property
    def permanent(self) -> bool:
        return self in {
            BeatmapSetStatus.RANKED,
            BeatmapSetStatus.APPROVED,
            BeatmapSetStatus.LOVED,
        }

    def ranked(self) -> bool:
        return self in {
            BeatmapSetStatus.RANKED,
            BeatmapSetStatus.APPROVED,
        }

    def has_leaderboard(self) -> bool:
        return self in {
            BeatmapSetStatus.RANKED,
            BeatmapSetStatus.APPROVED,
            BeatmapSetStatus.QUALIFIED,
            BeatmapSetStatus.LOVED,
        }



