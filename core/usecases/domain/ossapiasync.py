from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ossapi import OssapiAsync as BaseOssapiAsync
from core.models.domain.gameplay.mods import Mods

import core.usecases.domain.client_state as client_state_usecases

ONE_MINUTE = timedelta(minutes=1)


# https://osu.ppy.sh/community/forums/topics/1257747?n=5
class OssapiAsync(BaseOssapiAsync):
    def increment_api_calls(self) -> None:
        try:
            # If more than 1 minute has passed, reset the counter
            if datetime.now() - self.window_start >= ONE_MINUTE:
                self.api_calls = 0
                self.window_start = datetime.now()
        except AttributeError:
            # First call, initialize tracking
            self.api_calls = 0
            self.window_start = datetime.now()

        # For safety on user's API usage
        # https://osu.ppy.sh/docs/index.html#introduction:~:text=and%20javascript%20samples.-,Terms%20of%20Use,-Use%20the%20API
        # no more than 60 calls per min

        if self.api_calls >= 60:
            raise SystemExit(
                "API call limit exceeded: more than 60 calls in the last minute! Please contact a developer ASAP!!"
            )

        self.api_calls += 1

    async def _request(self, *args, **kwargs) -> Any:
        params = kwargs.get("params")

        self.increment_api_calls()

        if not isinstance(params, dict):
            print(f"DEBUG adapter - params is not a dict: {params}")
            return await super()._request(*args, **kwargs)

        if "mods" in params and isinstance(params["mods"], int):
            mods = Mods.from_stable_int(params["mods"])
            params["mods"] = mods.to_osu_api_v2()

        if "cursor" in params and "cursor_string" not in params:
            del params["cursor"]

            client_state = client_state_usecases.get_client_state()

            params["cursor_string"] = client_state.direct_reference.cursor_string

        return await super()._request(*args, **kwargs)