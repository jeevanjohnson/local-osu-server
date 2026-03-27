from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ossapi import OssapiAsync as BaseOssapiAsync
from ossapi.mod import Mod

import usecases.application.client.state

ONE_MINUTE = timedelta(minutes=1)


# https://osu.ppy.sh/community/forums/topics/1257747?n=5
class OssapiAsync(BaseOssapiAsync):
    @staticmethod
    def _mods_int_to_array(mods_value: int) -> list[str]:
        if mods_value == 0:
            return ["NM"]

        mod_combo = Mod(mods_value)
        return [mod.short_name() for mod in mod_combo.decompose(clean=True)]

    @staticmethod
    def _normalize_query_values(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: OssapiAsync._normalize_query_values(val)
                for key, val in value.items()
            }

        if isinstance(value, list):
            return [OssapiAsync._normalize_query_values(v) for v in value]

        mod_value = getattr(value, "value", None)
        if isinstance(mod_value, int):
            return mod_value

        return value

    async def _request(self, type_, method, url, params=None, data=None):
        if params is None:
            params = {}
        if data is None:
            data = {}

        params = self._normalize_query_values(params)
        data = self._normalize_query_values(data)

        if isinstance(params, dict):
            if "mods" in params and isinstance(params["mods"], int):
                # mod int to ?mods[]=EZ&mods[]=HD
                params["mods"] = self._mods_int_to_array(params["mods"])

            print(f"DEBUG adapter params keys: {params.keys()}")
            print(f"DEBUG adapter params: {params}")

            if "cursor" in params and "cursor_string" not in params:
                del params["cursor"]

                # Retrive cursor_string from session
                stored_cursor = (
                    await usecases.application.client.state.get_direct_cursor_string()
                )
                print(f"DEBUG adapter - using stored cursor: {stored_cursor}")
                params["cursor_string"] = stored_cursor

        # Initialize or reset rate limit window
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

        return await super()._request(type_, method, url, params=params, data=data)
