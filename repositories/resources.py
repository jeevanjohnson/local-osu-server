"""
Purpose/Domain/Concept:
- Contains the repository related to the "resources" folder
"""

from pathlib import Path

class ResourcesRepository:
    def __init__(self) -> None:
        self.resource_path = Path("./resources")
        self.seasonal_images = self.resource_path / "seasonal_images"
        self.menu_icon = self.resource_path / "menu_icon.png"
    
    def exists(self) -> bool:
        assert self.resource_path.exists(), "Resources folder does not exist!"
        assert self.seasonal_images.exists(), "Seasonal images folder does not exist!"
        assert self.menu_icon.exists(), "Menu icon does not exist!"
        return True

    def get_menu_icon(self) -> Path:
        return self.menu_icon