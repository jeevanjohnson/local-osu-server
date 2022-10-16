import urllib.parse
from typing import Any


def build_url(url: str, parameters: dict[str, Any]) -> str:
    if "?" in url:
        return url + urllib.parse.urlencode(parameters)
    else:
        return url + "?" + urllib.parse.urlencode(parameters)
