"""
Purpose/Domain/Concept:
- This file contains the repository (database interactions) related profiles.json file.
"""

from database.jsonfile import JsonFile
from models.database.profiles import ProfileData, Profile, Performance, Settings, osuTrainerBeatmapConfig
from osuProtocol.server_packets import osuGameMode
from pathlib import Path
from osuProtocol.server_packets import osuCountryCode

class ProfilesRepository:
    def __init__(self, path: Path):
        self.profiles = JsonFile[Profile](path)

    def get_profiles(self) -> Profile | None:
        with self.profiles as profiles:
            if not profiles:
                return None
            
            return profiles
    
    def get_profile(self, profile_name: str) -> Profile | None:
        with self.profiles as profiles:
            if profile_name in profiles:
                return {
                    profile_name: profiles[profile_name]
                }
            
            return None
    
    def create_new_profile(self, profile_name: str) -> None:
        with self.profiles as profiles:
            if profile_name in profiles:
                raise ValueError("Profile already exists.")
            
            default_performance = Performance(
                rank=0,
                accuracy=0.0,
                playcount=0,
                total_score=0,
                ranked_score=0,
                performance_points=0,
            )

            performance =  {
                "0": default_performance,
                "1": default_performance,
                "2": default_performance,
                "3": default_performance,
            }

            profiles[profile_name] = ProfileData(
                profile_picture = None,
                friend_ids = [],
                country_code = osuCountryCode.NA.value,
                performance = performance,
                notes=None,
                settings = Settings(
                    relax_submission=False,
                    auto_pilot_submission=False,
                    score_v2_submission=False,
                    force_scorev2=False,
                    force_nf=False,
                    osu_trainer_beatmaps=osuTrainerBeatmapConfig(
                        allow_submission=True,
                        sync_rank_status_with_bancho=True,
                    ),
                    self_rank=False
                ),
            )

    def create_profile(self, profile_name: str, profile_data: ProfileData) -> None:
        with self.profiles as profiles:
            profiles[profile_name] = profile_data
        
    def delete_profile(self, profile_name: str) -> None:
        with self.profiles as profiles:
            if profile_name in profiles:
                del profiles[profile_name]
    
    def update_profile(self, profile_name: str, profile_data: ProfileData) -> None:
        with self.profiles as profiles:
            if profile_name in profiles:
                profiles[profile_name] = profile_data