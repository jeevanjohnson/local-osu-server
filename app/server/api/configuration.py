from fastapi.routing import APIRouter
from fastapi.routing import APIRouter
from fastapi import Response
from dotenv import set_key
from fastapi import Request, Body, Depends
from .models import configuration as configuration_models

# TODO: find a different place to put this
# because it reality, this should not be in the api section
# in fact this shouldn't be in the server section
# this should be somewhere else in between the web client and the server
# because the web client should be able to access the osu path
# but I haven't figured that out yet

api_configuration_router = APIRouter(prefix="/api/v1/configuration")

def get_configuration(
    from_onboarding: bool = False,
    configuration: dict = Body(...)
) -> configuration_models.ConfigurationUpdate:
    
    if from_onboarding:
        return configuration_models.ConfigurationUpdate(
            osu_path=configuration["osu_path"],
            display_pp_on_leaderboard=configuration["display_pp_on_leaderboard"] == "on",
            rank_scores_by_pp_or_score=configuration["rank_scores_by_pp_or_score"] == "on",
            num_scores_seen_on_leaderboards=int(configuration["num_scores_seen_on_leaderboards"]),
            allow_pp_from_modified_maps=configuration["allow_pp_from_modified_maps"] == "on",
            osu_api_key=configuration["osu_api_key"],
            osu_daily_api_key=configuration["osu_daily_api_key"],
            osu_api_v2_key=configuration["osu_api_v2_key"],
            osu_username=configuration["osu_username"],
            osu_password=configuration["osu_password"],
            mitmproxy=None,
            cloudflare=None,
            developer=None
        )
    else:
        return configuration_models.ConfigurationUpdate(**configuration)

def update_env_file(
    new_configuration: configuration_models.ConfigurationUpdate
) -> None: # needs success case
    
    if new_configuration.osu_path:
        set_key(dotenv_path="./.env", key_to_set="OSU_PATH", value_to_set=new_configuration.osu_path)
    
    if new_configuration.display_pp_on_leaderboard:
        set_key(dotenv_path="./.env", key_to_set="DISPLAY_PP_ON_LEADERBOARD", value_to_set=str(new_configuration.display_pp_on_leaderboard))
    
    if new_configuration.rank_scores_by_pp_or_score:
        set_key(dotenv_path="./.env", key_to_set="RANK_SCORES_BY_PP_OR_SCORE", value_to_set=str(new_configuration.rank_scores_by_pp_or_score))
    
    if new_configuration.num_scores_seen_on_leaderboards:
        set_key(dotenv_path="./.env", key_to_set="NUM_SCORES_SEEN_ON_LEADERBOARDS", value_to_set=str(new_configuration.num_scores_seen_on_leaderboards))
    
    if new_configuration.allow_pp_from_modified_maps:
        set_key(dotenv_path="./.env", key_to_set="ALLOW_PP_FROM_MODIFIED_MAPS", value_to_set=str(new_configuration.allow_pp_from_modified_maps))
    
    if new_configuration.osu_api_key:
        set_key(dotenv_path="./.env", key_to_set="OSU_API_KEY", value_to_set=new_configuration.osu_api_key)
    
    if new_configuration.osu_daily_api_key:
        set_key(dotenv_path="./.env", key_to_set="OSU_DAILY_API_KEY", value_to_set=new_configuration.osu_daily_api_key)
    
    if new_configuration.osu_api_v2_key:
        set_key(dotenv_path="./.env", key_to_set="OSU_API_V2_KEY", value_to_set=new_configuration.osu_api_v2_key)
    
    if new_configuration.osu_username:
        set_key(dotenv_path="./.env", key_to_set="OSU_USERNAME", value_to_set=new_configuration.osu_username)
    
    if new_configuration.osu_password:
        set_key(dotenv_path="./.env", key_to_set="OSU_PASSWORD", value_to_set=new_configuration.osu_password)

    if new_configuration.mitmproxy:
        set_key(dotenv_path="./.env", key_to_set="MITMPROXY", value_to_set=str(new_configuration.mitmproxy))
    
    if new_configuration.cloudflare:
        set_key(dotenv_path="./.env", key_to_set="CLOUDFLARE", value_to_set=str(new_configuration.cloudflare))
        
    if new_configuration.developer:
        set_key(dotenv_path="./.env", key_to_set="DEVELOPER", value_to_set=str(new_configuration.developer))
    

# update .env file
@api_configuration_router.post("/update")
async def update_configuration(
    new_configuration: configuration_models.ConfigurationUpdate = Depends(get_configuration)
):
    update_env_file(new_configuration)
    
    return Response(status_code=200, content="Configuration updated")