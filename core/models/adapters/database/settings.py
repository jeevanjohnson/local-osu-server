from jays_tools.sql_database import MigratableSQLModel
from pydantic import Field


class ProfileSettingsV1(MigratableSQLModel, table=True):
    profile_name: str = Field(default="")

    amount_of_visible_leaderboard_scores: int = Field(default=50, ge=1, le=100)
    show_lazer_scores_on_leaderboard: bool = Field(default=True)
    show_only_lazer_scores_on_leaderboard_with_score_v2_enabled: bool = Field(
        default=False
    )
    pp_leaderboards: bool = Field(default=False)

    allow_relax_submission: bool = Field(default=False)
    allow_auto_pilot_submission: bool = Field(default=False)
    allow_score_v2_submission: bool = Field(default=False)
    force_score_v2: bool = Field(default=False)
    force_nf: bool = Field(default=False)


ProfileSettings = ProfileSettingsV1
