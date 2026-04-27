from dataclasses import dataclass

from archieve.models.bancho.scores import LazerScore, Score, StableScore
from archieve.models.database.beatmaps import CurrentBeatmap as Beatmap
from archieve.models.database.scores import CurrentScore as ProfileScore
from archieve.models.domain.gameplay import osuMods
from archieve.models.domain.scores import AcceptedScores, AllScores, ScoringAlgorithm
from core.adapters.osu_protocol.osu.types import osuMapStatus

LEADERBOARD_SCORE_FMT = (
    "{id}|{name}|{score}|{max_combo}|"
    "{n50}|{n100}|{n300}|{nmiss}|{nkatu}|{ngeki}|"
    "{perfect}|{mods}|{userid}|{rank}|{time}|{has_replay}"
)

EpochTime = int


@dataclass
class LeaderboardScore:
    """
    Represents a single score on the leaderboard.
    """

    score_id: int
    username: str
    score: int
    max_combo: int
    count50: int
    count100: int
    count300: int
    count_miss: int
    countkatu: int
    countgeki: int
    perfect: bool
    enabled_mods: osuMods
    user_id: int
    position: int
    time_set_epoch: int
    replay_available: bool

    def serialize(self) -> str:
        return LEADERBOARD_SCORE_FMT.format(
            id=self.score_id,
            name=self.username,
            score=self.score,
            max_combo=self.max_combo,
            n50=self.count50,
            n100=self.count100,
            n300=self.count300,
            nmiss=self.count_miss,
            nkatu=self.countkatu,
            ngeki=self.countgeki,
            perfect=int(self.perfect),
            mods=self.enabled_mods,
            userid=self.user_id,
            rank=self.position,
            time=self.time_set_epoch,
            has_replay=int(self.replay_available),
        )

    def __repr__(self) -> str:
        return self.serialize()

    def name_override(self, new_name: str) -> None:
        self.username = new_name

    # @classmethod
    # def from_score(
    #     cls,
    #     score: Score | ProfileScore,
    #     position: int,
    #     ingame_score: int,
    #     from_difficulty_adjusted: bool = False,
    #     truncate_username: bool = False,
    # ) -> "LeaderboardScore":
    #     stable_mods, lazer_mods = score.enabled_mods.to_stable_mods()
    #     has_lazer_rate_change = any(m.endswith("x") for m in lazer_mods)

    #     if isinstance(score, LazerScore):
    #         title = f"[LAZER] {score.username}"

    #         total_lazer_mods = len(lazer_mods)

    #         if lazer_mods:
    #             title += " ("

    #             for i, lazer_mod in enumerate(lazer_mods):
    #                 if lazer_mod == "DA":
    #                     continue

    #                 if lazer_mod.endswith("x"):  # Rate change
    #                     # remove any rate changing mod
    #                     # so more space can be given to lazer-exclusive mods in the title
    #                     stable_mods = (
    #                         stable_mods
    #                         & ~osuMods.DOUBLETIME
    #                         & ~osuMods.HALFTIME
    #                         & ~osuMods.NIGHTCORE
    #                     )

    #                     if float(lazer_mod[:-1]) < 1.0:
    #                         lazer_mod = lazer_mod.replace("0.", ".", count=1)

    #                 if i == total_lazer_mods - 1:
    #                     title += lazer_mod
    #                 else:
    #                     title += lazer_mod + ","

    #             title += ")"
    #     else:
    #         title = score.username

    #     if "NC" in score.enabled_mods:
    #         # Client needs this in order to actual speed up the
    #         # replay properly
    #         stable_mods |= osuMods.DOUBLETIME

    #         if isinstance(score, LazerScore):
    #             stable_mods |= osuMods.NIGHTCORE

    #     if from_difficulty_adjusted and not isinstance(score, ProfileScore):
    #         # https://capitalizemytitle.com/small-text-converter/
    #         title = f"[ᵒᵍ ᵈⁱᶠᶠ] {title}"

    #         stable_mods = (
    #             stable_mods
    #             & ~osuMods.DOUBLETIME
    #             & ~osuMods.HALFTIME
    #             & ~osuMods.NIGHTCORE
    #         )

    #         if isinstance(score, StableScore):
    #             if "DT" in score.enabled_mods or "NC" in score.enabled_mods:
    #                 title += " (1.5x)"
    #             elif "HT" in score.enabled_mods or "DC" in score.enabled_mods:
    #                 title += " (.75x)"
    #             else:
    #                 title += " (1x)"
    #         elif isinstance(score, LazerScore):
    #             if not has_lazer_rate_change:
    #                 if "DT" in score.enabled_mods or "NC" in score.enabled_mods:
    #                     title += " (1.5x)"
    #                 elif "HT" in score.enabled_mods or "DC" in score.enabled_mods:
    #                     title += " (.75x)"
    #                 else:
    #                     title += " (1x)"

    #     if truncate_username and len(title) > 15 + 3:  # 15 chars + 3 for "..."
    #         title = title[:15] + "..."  # Truncate username to 20 characters

    #     if isinstance(score, ProfileScore):
    #         score_id = -score.id
    #         max_combo = score.combo
    #         user_id = 2
    #         replay_available = score.replay_frames is not None
    #     else:
    #         user_id = score.user_id
    #         score_id = score.score_id
    #         max_combo = score.combo.actual
    #         replay_available = score.replay_available

    #     if not stable_mods & osuMods.SCOREV2:
    #         if not isinstance(score, ProfileScore):
    #             # This allows watching replays
    #             # and playing w/ score v2 making the
    #             # ranking up the map feel with the lb on more
    #             # realistic to bancho/lazer
    #             stable_mods |= osuMods.SCOREV2
    #         else:
    #             # TODO: profile setting?
    #             # cause when you actually play the map the side leaderboards
    #             # you just become number 1 cause client will calculate score
    #             # by legacy algorithm instead of score v2, which is what the profile scores are stored with
    #             # & the replay's acc will be off cause of slider acc
    #             pass

    #     return cls(
    #         score_id=score_id,
    #         username=title,
    #         score=ingame_score,
    #         max_combo=max_combo,
    #         count50=score.count50,
    #         count100=score.count100,
    #         count300=score.count300,
    #         count_miss=score.count_miss,
    #         countkatu=0,
    #         countgeki=0,
    #         perfect=score.perfect,
    #         enabled_mods=stable_mods,
    #         user_id=user_id,
    #         position=position,
    #         time_set=score.time_set,
    #         replay_available=replay_available,
    #     )


STARTING_LB_FORMAT = (
    "{beatmap_status}|false|{beatmap_id}|{beatmap_set_id}|{num_of_scores}\n0\n"
    "[bold:0,size:20]{artist_unicode}|{title_unicode}\n10.0\n"
)


@dataclass
class LeaderboardHeader:
    """
    Represents the header of a leaderboard, containing metadata about the leaderboard.
    """

    beatmap_status: osuMapStatus
    beatmap_id: int
    beatmap_set_id: int
    num_of_scores: int
    artist: str
    title: str

    def serialize(self) -> str:
        return STARTING_LB_FORMAT.format(
            beatmap_status=self.beatmap_status.value,
            beatmap_id=self.beatmap_id,
            beatmap_set_id=self.beatmap_set_id,
            num_of_scores=self.num_of_scores,
            artist_unicode=self.artist,
            title_unicode=self.title,
        )


class Leaderboard:
    """
    Represents a full leaderboard, including the header and the list of scores.
    """

    def __init__(
        self,
        header: LeaderboardHeader,
        scores: list[LeaderboardScore] | None = None,
        personal_best: LeaderboardScore | None = None,
    ):
        self.header = header

        if scores is None:
            self.scores = []
        else:
            self.scores = scores

        self.personal_best = personal_best

    def serialize(self) -> bytes:
        if self.header.beatmap_status < 1:
            return f"{self.header.beatmap_status.value}|false".encode()

        buffer = bytearray()

        buffer += self.header.serialize().encode()

        raw_personal_best = b"\n"
        if self.personal_best:
            raw_personal_best = self.personal_best.serialize().encode() + b"\n"

        buffer += raw_personal_best

        for score in self.scores:
            buffer += score.serialize().encode() + b"\n"

        return bytes(buffer)

# class LeaderboardWithScores(Leaderboard):
#     # # log
#     def __init__(
#         self,
#         beatmap: "Beatmap",
#         scores: AllScores,
#         personal_best: ProfileScore | None,
#         scoring_algorithm: ScoringAlgorithm,
#         difficulty_adjusted: bool,
#         limit: int,
#         accepted_scores: AcceptedScores,
#         profile_name: str,
#     ) -> None:
#         self.beatmap = beatmap
#         self.scores = scores
#         self.personal_best = personal_best
#         self.scoring_algorithm = scoring_algorithm
#         self.difficulty_adjusted = difficulty_adjusted
#         self.limit = limit
#         self.accepted_scores = accepted_scores
#         self.profile_name = profile_name

#         if self.personal_best is not None:
#             if self.personal_best not in self.scores:
#                 self.scores.append(self.personal_best)

#         self.scores.sort(self.scoring_algorithm)

#     @property
#     def play_count(self) -> int:
#         return self.beatmap.play_count

#     @property
#     def pass_count(self) -> int:
#         if self.beatmap.pass_count < 1:
#             return 1

#         return self.beatmap.pass_count

#     def personal_best_position(self) -> int:
#         if self.personal_best is None:
#             return 0

#         return self.scores.position_of_score(
#             self.personal_best,
#             self.scoring_algorithm,
#             beatmap_pass_count=self.beatmap.pass_count,
#             leaderboard_limit=self.limit,
#         )

#     def serialize_personal_best(self) -> LeaderboardScore | None:
#         if self.personal_best is None:
#             return None

#         if (
#             self.scoring_algorithm == ScoringAlgorithm.PP
#             and self.beatmap.can_display_pp
#         ):
#             ingame_score = self.personal_best.performance_points or 0
#         else:
#             ingame_score = self.personal_best.total_score

#         return LeaderboardScore.from_score(
#             score=self.personal_best,
#             position=self.personal_best_position(),
#             ingame_score=ingame_score,
#             from_difficulty_adjusted=self.difficulty_adjusted,
#         )

#     def serialize(self) -> bytes:
#         leaderboard_header = LeaderboardHeader(
#             beatmap_status=self.beatmap.status[self.profile_name],
#             beatmap_id=self.beatmap.id,
#             beatmap_set_id=self.beatmap.set_id,
#             num_of_scores=self.beatmap.pass_count,
#             artist=self.beatmap.artist,
#             title=self.beatmap.title,
#         )

#         leaderboard = Leaderboard(
#             header=leaderboard_header,
#             personal_best=self.serialize_personal_best(),
#         )

#         leaderboard_scores = []

#         seen_self = False
#         for index, score in enumerate(self.scores[: self.limit]):
#             if (
#                 self.scoring_algorithm == ScoringAlgorithm.PP
#                 and self.beatmap.can_display_pp
#             ):
#                 ingame_score = score.performance_points or 0
#             else:
#                 ingame_score = score.total_score

#             if seen_self:
#                 score.username += " " * (index + 1)

#             if score == self.personal_best:
#                 seen_self = True

#             leaderboard_score = LeaderboardScore.from_score(
#                 score=score,
#                 position=index + 1,
#                 ingame_score=ingame_score,
#                 from_difficulty_adjusted=self.difficulty_adjusted,
#             )
#             leaderboard_scores.append(leaderboard_score)

#         if not seen_self and leaderboard.personal_best:
#             # if personal best not in top scores, calc its position
#             # using interpolation
#             leaderboard.personal_best.position = self.personal_best_position()

#         leaderboard.scores = leaderboard_scores

#         return leaderboard.serialize()


class GraveyardLeaderboard(Leaderboard):
    """
    Represents a leaderboard for beatmaps that are in the graveyard.
    """

    def __init__(self):
        super().__init__(
            LeaderboardHeader(
                beatmap_status=osuMapStatus.PENDING,
                beatmap_id=0,
                beatmap_set_id=0,
                num_of_scores=0,
                artist="",
                title="",
            ),
            [],
        )


class UpdateBeatmapRequestLeaderboard(Leaderboard):
    """
    Represents a leaderboard for beatmaps that have been updated.
    """

    def __init__(self):
        super().__init__(
            LeaderboardHeader(
                beatmap_status=osuMapStatus.UPDATE_AVAILABLE,
                beatmap_id=0,
                beatmap_set_id=0,
                num_of_scores=0,
                artist="",
                title="",
            ),
            [],
        )


class NotSubmittedLeaderboard(Leaderboard):
    """
    Represents a leaderboard for beatmaps that have not been submitted.
    """

    def __init__(self):
        super().__init__(
            LeaderboardHeader(
                beatmap_status=osuMapStatus.NOT_SUBMITTED,
                beatmap_id=0,
                beatmap_set_id=0,
                num_of_scores=0,
                artist="",
                title="",
            ),
            [],
        )
