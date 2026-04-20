from core.models.profile import Profile
from jays_tools import JsonCollection
from core.constants import PROFILES

class ProfilesRepository:
    def __init__(self) -> None:
        self.collection = JsonCollection(
            path=PROFILES, 
            model=Profile
        )
    
    def get_profiles(self) -> dict[str, Profile]:
        return self.collection.get_all()

    def profile_exists(self, profile_name: str) -> bool:
        return self.collection.exists(profile_name)

    def get_profile(self, profile_name: str) -> Profile | None:
        profile_json_database = self.collection.get(profile_name)
        profile = profile_json_database.get_database()
        return profile

    def create_profile(self, profile_name: str, profile: Profile) -> Profile:
        return self.collection.create(profile_name, profile)
    
    def create_new_profile(self, profile_name: str) -> Profile:
        return self.collection.create(profile_name, Profile())

    def update_profile(self, profile_name: str, profile: Profile) -> Profile:
        return self.collection.update(profile_name, profile)

    def delete_profile(self, profile_name: str) -> None:
        self.collection.delete(profile_name)