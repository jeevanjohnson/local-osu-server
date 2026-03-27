

from dataclasses import dataclass
from datetime import datetime



@dataclass
class Achievement:
    image_url: str
    title: str
    description: str

    def serialize(self) -> str:
        return f"{self.image_url}+{self.title}+{self.description}"


class Achievements(list[Achievement]):
    def serialize(self) -> str:
        return "/".join(achievement.serialize() for achievement in self)


@dataclass
class ChartColumn:
    name: str
    before: float | None = None
    after: float | None = None

    def serialize(self) -> str:
        return (
            f"{self.name}Before:{self.before or ''}|{self.name}After:{self.after or ''}"
        )


@dataclass
class Rank(ChartColumn):
    name: str = "rank"


@dataclass
class RankedScore(ChartColumn):
    name: str = "rankedScore"


@dataclass
class TotalScore(ChartColumn):
    name: str = "totalScore"


@dataclass
class MaxCombo(ChartColumn):
    name: str = "maxCombo"


@dataclass
class Accuracy(ChartColumn):
    name: str = "accuracy"


@dataclass
class PerformancePoints(ChartColumn):
    name: str = "pp"


@dataclass
class Chart:
    rank: Rank
    ranked_score: RankedScore
    total_score: TotalScore
    max_combo: MaxCombo
    accuracy: Accuracy
    pp: PerformancePoints

    def serialize(self) -> list[str]:
        return [
            self.rank.serialize(),
            self.ranked_score.serialize(),
            self.total_score.serialize(),
            self.max_combo.serialize(),
            self.accuracy.serialize(),
            self.pp.serialize(),
        ]


class BeatmapChart(Chart):
    pass


class OverallRankingChart(Chart):
    pass


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

    @property
    def beatmap_url(self) -> str:
        return f"https://osu.ppy.sh/b/{self.beatmap_id}"

    @property
    def chart_url(self) -> str:
        # TODO: Redirect to GUI?
        return "https://osu.ppy.sh/u/2"

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
            f"chartUrl:{self.beatmap_url}",
            "chartName:Beatmap Ranking",
            *self.beatmap_chart.serialize(),
            f"onlineScoreId:{self.score_id}",
            "\n",
            # overall ranking chart
            "chartId:overall",
            f"chartUrl:{self.chart_url}",
            "chartName:Overall Ranking",
            *self.overall_ranking_chart.serialize(),
            f"achievements-new:{self.achievements.serialize()}",
        ]

        return "|".join(submission_charts).encode()


UNRANKED_CHARTS = SubmissionCharts(
    beatmap_id=0,
    beatmap_set_id=0,
    beatmap_playcount=0,
    beatmap_passcount=0,
    last_updated=datetime.now(),
    score_id=0,
    beatmap_chart=BeatmapChart(
        rank=Rank(name="rank"),
        ranked_score=RankedScore(name="rankedScore"),
        total_score=TotalScore(name="totalScore"),
        max_combo=MaxCombo(name="maxCombo"),
        accuracy=Accuracy(name="accuracy"),
        pp=PerformancePoints(name="pp"),
    ),
    overall_ranking_chart=OverallRankingChart(
        rank=Rank(name="rank"),
        ranked_score=RankedScore(name="rankedScore"),
        total_score=TotalScore(name="totalScore"),
        max_combo=MaxCombo(name="maxCombo"),
        accuracy=Accuracy(name="accuracy"),
        pp=PerformancePoints(name="pp"),
    ),
    achievements=Achievements(),
)