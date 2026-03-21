"""
Purpose/Domain/Concept:
- This file models bancho's api requests and response schemas related to assets.ppy.sh
"""

from typing import TypedDict

"""
{
  "images": [
    {
      "image": "https://assets.ppy.sh/main-menu/2026-spring-fanart-submissions@2x.png",
      "url": "https://osu.ppy.sh/home/news/2026-03-06-spring-fanart-contest",
      "IsCurrent": true,
      "begins": null,
      "expires": "2026-03-27T18:00:00+00:00"
    }
  ]
}
"""


class MenuContentImage(TypedDict):
    image: str
    url: str
    IsCurrent: bool
    begins: str | None
    expires: str | None


class MenuContentResponse(TypedDict):
    images: list[MenuContentImage]


MenuIconResponse = MenuContentResponse
