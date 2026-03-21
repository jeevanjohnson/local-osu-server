"""
Purpose/Domain/Concept:
- This file contains the logic related to assets.ppy.sh
"""

from models.bancho.assets import MenuContentImage, MenuIconResponse


def menu_content_response() -> MenuIconResponse:
    return MenuIconResponse(
        images=[
            MenuContentImage(
                image="https://cdn.discordapp.com/attachments/731243591392821299/1479379494962991135/3372.png?ex=69b65f05&is=69b50d85&hm=f3ad54c6d1e2c43676065fa7efe61a38f5f037c07873ec88fd4d6bf925c9a0d3&",
                url="https://github.com/jeevanjohnson/local-osu-server",
                IsCurrent=True,
                begins=None,
                expires=None,
            )
        ]
    )
