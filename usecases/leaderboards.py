from typing import TYPE_CHECKING

from models.database.scores import (
    CurrentScore as Score,
)
from osuProtocol.client_web import Leaderboard as ClientLeaderboard
from osuProtocol.client_web import LeaderboardHeader, LeaderboardScore

if TYPE_CHECKING:
    from models.database.beatmaps import (
        CurrentBeatmap as Beatmap,
    )
    from usecases.scores import AllScores

import usecases.bancho_scores
import usecases.scores
import usecases.sessions
from adapters import log_time
from models.database.profiles import (
    CurrentProfile as Profile,
)
from models.database.profiles import (
    CurrentSettings as Settings,
)
from models.domain.gameplay import Mods, osuGameMode
from osuProtocol.client_web import LeaderboardType, ScoringAlgorithm
from usecases.bancho_scores import AcceptedScores
from usecases.scores import AllScores

Position = int
TotalScore = int


class Leaderboard:
    # @log_time
    def __init__(
        self,
        beatmap: "Beatmap",
        scores: "AllScores",
        personal_best: Score | None,
        scoring_algorithm: ScoringAlgorithm,
        difficulty_adjusted: bool,
        truncate_usernames: bool,
        limit: int,
    ) -> None:
        self.beatmap = beatmap
        self.scores = scores
        self.personal_best = personal_best
        self.scoring_algorithm = scoring_algorithm
        self.difficulty_adjusted = difficulty_adjusted
        self.truncate_usernames = truncate_usernames
        self.limit = limit

        if self.personal_best is not None:
            if self.personal_best not in self.scores:
                self.scores.append(self.personal_best)

        self.scores.sort(self.scoring_algorithm)

    @property
    def play_count(self) -> int:
        return self.beatmap.play_count

    @property
    def pass_count(self) -> int:
        if self.beatmap.pass_count < 1:
            return 1

        return self.beatmap.pass_count

    def personal_best_position(self) -> int:
        if self.personal_best is None:
            return 0

        if self.personal_best in self.scores[: self.limit]:
            return self.scores.index(self.personal_best) + 1
        else:
            return self.scores.position_of_score(
                self.personal_best,
                self.scoring_algorithm,
                beatmap_pass_count=self.beatmap.pass_count,
            )

    def serialize_personal_best(self) -> LeaderboardScore | None:
        if self.personal_best is None:
            return None

        if (
            self.scoring_algorithm == ScoringAlgorithm.PP
            and self.beatmap.can_display_pp
        ):
            ingame_score = self.personal_best.performance_points or 0
        else:
            ingame_score = self.personal_best.total_score

        return LeaderboardScore.from_score(
            score=self.personal_best,
            position=self.personal_best_position(),
            ingame_score=ingame_score,
            from_difficulty_adjusted=self.difficulty_adjusted,
            truncate_username=self.truncate_usernames,
        )

    def serialize(self) -> bytes:
        leaderboard_header = LeaderboardHeader(
            beatmap_status=self.beatmap.status,
            beatmap_id=self.beatmap.id,
            beatmap_set_id=self.beatmap.set_id,
            num_of_scores=self.beatmap.pass_count,
            artist=self.beatmap.artist,
            title=self.beatmap.title,
        )

        leaderboard = ClientLeaderboard(
            header=leaderboard_header,
            personal_best=self.serialize_personal_best(),
        )

        leaderboard_scores = []

        seen_self = False
        for index, score in enumerate(self.scores[: self.limit]):
            if (
                self.scoring_algorithm == ScoringAlgorithm.PP
                and self.beatmap.can_display_pp
            ):
                ingame_score = score.performance_points or 0
            else:
                ingame_score = score.total_score

            if seen_self:
                score.username += " " * (index + 1)

            if score == self.personal_best:
                seen_self = True

            leaderboard_score = LeaderboardScore.from_score(
                score=score,
                position=index + 1,
                ingame_score=ingame_score,
                from_difficulty_adjusted=self.difficulty_adjusted,
                truncate_username=self.truncate_usernames,
            )
            leaderboard_scores.append(leaderboard_score)

        if not seen_self and leaderboard.personal_best:
            # if personal best not in top scores, calc its position
            # using interpolation
            leaderboard.personal_best.position = self.personal_best_position()

        leaderboard.scores = leaderboard_scores

        return leaderboard.serialize()


UserIDs = int

NO_LEADERBOARD_LIMIT = 1000000


class LeaderboardResolver:
    def __init__(self, profile_name: str, scoring_algorithm: ScoringAlgorithm) -> None:

        self.leaderboard: Leaderboard | None = None
        self.scoring_algorithm = scoring_algorithm
        self.profile_name = profile_name

    @log_time
    async def personal_scores_leaderboard(
        self,
        beatmap: "Beatmap",
        game_mode: osuGameMode,
    ) -> Leaderboard:
        personal_scores = await usecases.scores.get_scores_for_beatmap(
            beatmap=beatmap,
            profile_name=self.profile_name,
            game_mode=game_mode,
        )

        personal_scores.sort(self.scoring_algorithm)

        if personal_scores.scores:
            personal_best = personal_scores.scores[0]
        else:
            personal_best = None

        self.leaderboard = Leaderboard(
            beatmap=beatmap,
            scores=AllScores(personal_scores.scores),
            personal_best=personal_best,
            scoring_algorithm=self.scoring_algorithm,
            difficulty_adjusted=beatmap.difficulty_adjusted,
            truncate_usernames=False,
            limit=NO_LEADERBOARD_LIMIT,
        )

        return self.leaderboard

    @log_time
    async def friends_leaderboard(
        self,
        beatmap: "Beatmap",
        game_mode: osuGameMode,
        accepted_scores: AcceptedScores,
        friends: list[UserIDs],
    ) -> Leaderboard:
        friends_scores = await usecases.bancho_scores.get_friends_scores_for_beatmap(
            beatmap=beatmap,
            game_mode=game_mode,
            accepted_scores=accepted_scores,
            friends_user_ids=friends,
        )

        await usecases.sessions.update_avaliable_stable_replay_ids_from_scores(
            friends_scores
        )

        personal_best = await usecases.scores.personal_best_for_beatmap(
            beatmap=beatmap,
            profile_name=self.profile_name,
            game_mode=game_mode,
            scoring_algorithm=self.scoring_algorithm,
        )

        self.leaderboard = Leaderboard(
            beatmap=beatmap,
            scores=AllScores(friends_scores.scores),
            personal_best=personal_best,
            scoring_algorithm=self.scoring_algorithm,
            difficulty_adjusted=beatmap.difficulty_adjusted,
            truncate_usernames=False,
            limit=NO_LEADERBOARD_LIMIT,
        )

        return self.leaderboard

    @log_time
    async def selected_mods_leaderboard(
        self,
        beatmap: "Beatmap",
        game_mode: osuGameMode,
        accepted_scores: AcceptedScores,
        limit: int,
        mods: Mods,
    ) -> Leaderboard:
        bancho = await usecases.bancho_scores.get_mod_specific_scores_for(
            beatmap=beatmap,
            game_mode=game_mode,
            accepted_scores=accepted_scores,
            mods=mods,
            ranking_type=self.scoring_algorithm.to_api_v2(),
        )

        await usecases.sessions.update_avaliable_stable_replay_ids_from_scores(bancho)

        personal_best = await usecases.scores.personal_best_for_beatmap(
            beatmap=beatmap,
            profile_name=self.profile_name,
            game_mode=game_mode,
            scoring_algorithm=self.scoring_algorithm,
            mods=mods,
        )

        self.leaderboard = Leaderboard(
            beatmap=beatmap,
            scores=AllScores(bancho.all_scores),
            personal_best=personal_best,
            scoring_algorithm=self.scoring_algorithm,
            difficulty_adjusted=beatmap.difficulty_adjusted,
            truncate_usernames=False,
            limit=limit,
        )

        return self.leaderboard

    @log_time
    async def global_leaderboard(
        self,
        beatmap: "Beatmap",
        game_mode: osuGameMode,
        accepted_scores: AcceptedScores,
        limit: int,
    ) -> Leaderboard:

        bancho = await usecases.bancho_scores.get_any_scores_for(
            beatmap=beatmap,
            game_mode=game_mode,
            accepted_scores=accepted_scores,
            ranking_type=self.scoring_algorithm.to_api_v2(),
        )

        await usecases.sessions.update_avaliable_stable_replay_ids_from_scores(bancho)

        personal_best = await usecases.scores.personal_best_for_beatmap(
            beatmap=beatmap,
            profile_name=self.profile_name,
            game_mode=game_mode,
            scoring_algorithm=self.scoring_algorithm,
        )

        self.leaderboard = Leaderboard(
            beatmap=beatmap,
            scores=AllScores(bancho.all_scores),
            personal_best=personal_best,
            scoring_algorithm=self.scoring_algorithm,
            difficulty_adjusted=beatmap.difficulty_adjusted,
            truncate_usernames=False,
            limit=limit,
        )

        return self.leaderboard

    @log_time
    async def from_request(
        self,
        beatmap: "Beatmap",
        leaderboard_type: LeaderboardType,
        game_mode: osuGameMode,
        mods: Mods | None,
        accepted_scores: AcceptedScores,
        limit: int,
        friends: list[UserIDs],
    ) -> Leaderboard:

        if leaderboard_type == LeaderboardType.TOP:
            return await self.global_leaderboard(
                beatmap=beatmap,
                game_mode=game_mode,
                accepted_scores=accepted_scores,
                limit=limit,
            )
        elif leaderboard_type == LeaderboardType.MODS:
            assert mods is not None, "Mods must be provided for MODS leaderboard type."
            return await self.selected_mods_leaderboard(
                beatmap=beatmap,
                game_mode=game_mode,
                accepted_scores=accepted_scores,
                limit=limit,
                mods=mods,
            )
        elif leaderboard_type == LeaderboardType.FRIENDS:
            return await self.friends_leaderboard(
                beatmap=beatmap,
                game_mode=game_mode,
                accepted_scores=accepted_scores,
                friends=friends,
            )
        elif leaderboard_type == LeaderboardType.COUNTRY:
            # TODO: For now show all personal scores set on map
            # Maybe in the future allow the user to decided if they want this
            # Or country leaderboards since we can implement it
            return await self.personal_scores_leaderboard(
                beatmap=beatmap,
                game_mode=game_mode,
            )
        else:
            raise ValueError(f"Unsupported leaderboard type: {leaderboard_type}")


@log_time
async def from_request(
    beatmap: "Beatmap",
    leaderboard_type: LeaderboardType,
    game_mode: osuGameMode,
    mods: Mods | None,
    profile_name: str,
    profile: Profile,
    settings: Settings,
):
    if settings.leaderboard.show_lazer_scores_on_leaderboard:
        accepted_scores = AcceptedScores.BOTH
    else:
        accepted_scores = AcceptedScores.STABLE_ONLY

    if mods:
        if "SV2" in mods:
            if settings.score_v2_shows_lazer_only_leaderboard:
                accepted_scores = AcceptedScores.LAZER_ONLY

        # For searching for scores, we don't need to consider these
        # and if you really wanted to see the relax lb for lazer
        # just go to lazer lmao
        # jk TODO: setting?
        for redundant_mod in ["RX", "AP", "SV2"]:
            if redundant_mod in mods:
                mods.remove(redundant_mod)

    leaderboard_resolver = LeaderboardResolver(
        profile_name=profile_name, scoring_algorithm=settings.scoring_algorithm
    )

    return await leaderboard_resolver.from_request(
        beatmap=beatmap,
        leaderboard_type=leaderboard_type,
        game_mode=game_mode,
        mods=mods,
        accepted_scores=accepted_scores,
        limit=settings.leaderboard.leaderboard_score_limit,
        friends=profile.friend_ids,
    )
