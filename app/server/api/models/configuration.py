from pydantic import BaseModel

class ConfigurationUpdate(BaseModel):
    mitmproxy: bool | None = None
    cloudflare: bool | None = None
    developer: bool | None = None
    osu_path: str | None = None
    display_pp_on_leaderboard: bool | None = None
    rank_scores_by_pp_or_score: bool | None = None
    num_scores_seen_on_leaderboards: int | None = None
    allow_pp_from_modified_maps: bool | None = None
    osu_api_key: str | None = None
    osu_daily_api_key: str | None = None
    osu_api_v2_key: str | None = None
    # TODO: find an alternative to needing the user's osu username and password
    osu_username: str | None = None
    osu_password: str | None = None