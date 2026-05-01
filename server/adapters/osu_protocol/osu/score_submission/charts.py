from dataclasses import dataclass, field
from datetime import datetime
from constants import OsuClient
from server.adapters.osu_protocol.osu.score_submission.achievements import Achievements


@dataclass
class ChartEntry:
    before: float | None = None
    after: float | None = None

    def serialize(self, name: str) -> str:
        return f"{name}Before:{self.before or ''}|{name}After:{self.after or ''}"


@dataclass
class Chart:
    rank:          ChartEntry = field(default_factory=ChartEntry)
    ranked_score:  ChartEntry = field(default_factory=ChartEntry)
    total_score:   ChartEntry = field(default_factory=ChartEntry)
    max_combo:     ChartEntry = field(default_factory=ChartEntry)
    accuracy:      ChartEntry = field(default_factory=ChartEntry)
    pp:            ChartEntry = field(default_factory=ChartEntry)

    def serialize(self) -> list[str]:
        return [
            self.rank.serialize("rank"),
            self.ranked_score.serialize("rankedScore"),
            self.total_score.serialize("totalScore"),
            self.max_combo.serialize("maxCombo"),
            self.accuracy.serialize("accuracy"),
            self.pp.serialize("pp"),
        ]


BeatmapChart = Chart
OverallRankingChart = Chart


@dataclass
class SubmissionCharts:
    beatmap_id: int
    beatmap_set_id: int
    beatmap_playcount: int
    beatmap_passcount: int
    last_updated: datetime
    score_id: int
    beatmap_chart: BeatmapChart
    overall_ranking_chart: OverallRankingChart
    achievements: Achievements

    def serialize(self) -> bytes:
        submission_charts = [
            f"beatmapId:{self.beatmap_id}",
            f"beatmapSetId:{self.beatmap_set_id}",
            f"beatmapPlaycount:{self.beatmap_playcount}",
            f"beatmapPasscount:{self.beatmap_passcount}",
            f"approvedDate:{self.last_updated}",
            "\n",
            # beatmap ranking chart
            "chartId:beatmap",
            f"chartUrl:https://osu.ppy.sh/b/{self.beatmap_id}",
            "chartName:Beatmap Ranking",
            *self.beatmap_chart.serialize(),
            f"onlineScoreId:{self.score_id}",
            "\n",
            # overall ranking chart
            "chartId:overall",
            f"chartUrl:https://{OsuClient.REQUEST_URL}/u/2",
            "chartName:Overall Ranking",
            *self.overall_ranking_chart.serialize(),
            f"achievements-new:{self.achievements.serialize()}",
        ]

        return "|".join(submission_charts).encode()


def empty_submission_charts() -> SubmissionCharts:
    return SubmissionCharts(
        beatmap_id=0,
        beatmap_set_id=0,
        beatmap_playcount=0,
        beatmap_passcount=0,
        last_updated=datetime.now(),
        score_id=0,
        beatmap_chart=BeatmapChart(),
        overall_ranking_chart=OverallRankingChart(),
        achievements=Achievements(),
    )


def no_leaderboard_submission_charts(
    beatmap_total_score_before: int,
    beatmap_total_score_after: int,

    overall_total_score_before: int,
    overall_total_score_after: int,
) -> SubmissionCharts:
    charts = empty_submission_charts()

    charts.beatmap_chart.ranked_score.before = beatmap_total_score_before
    charts.beatmap_chart.ranked_score.after = beatmap_total_score_after

    charts.overall_ranking_chart.ranked_score.before = overall_total_score_before
    charts.overall_ranking_chart.ranked_score.after = overall_total_score_after

    return charts
