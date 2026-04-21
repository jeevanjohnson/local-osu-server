from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ossapi import OssapiAsync as BaseOssapiAsync
from ossapi import Mod
from core.models.domain.gameplay.mods import Mods

import core.usecases.domain.client_state as client_state_usecases

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

        # Handle ossapi enums and mod objects - extract the value attribute
        if hasattr(value, "value"):
            return OssapiAsync._normalize_query_values(value.value)

        return value

    def _check_and_increment_rate_limit(self) -> None:
        """Enforce API rate limit of 60 calls per minute."""
        try:
            if datetime.now() - self.window_start >= ONE_MINUTE:
                self.api_calls = 0
                self.window_start = datetime.now()
        except AttributeError:
            # First call, initialize tracking
            self.api_calls = 0
            self.window_start = datetime.now()

        if self.api_calls >= 60:
            raise SystemExit(
                "API call limit exceeded: more than 60 calls in the last minute! "
                "Please contact a developer ASAP!!"
            )

        self.api_calls += 1

    async def _request(self, type_, method, url, params=None, data=None) -> Any:
        # Normalize query values (convert ossapi objects to primitives)
        params = self._normalize_query_values(params or {})
        data = self._normalize_query_values(data or {})

        # Convert mod integers to mods array format
        if "mods" in params and isinstance(params["mods"], int):
            params["mods"] = self._mods_int_to_array(params["mods"])

        # Handle direct cursor storage
        if "cursor" in params and "cursor_string" not in params:
            del params["cursor"]
            client_state = client_state_usecases.get_client_state()
            params["cursor_string"] = client_state.direct_reference.cursor_string

        # Check rate limits
        self._check_and_increment_rate_limit()

        print(f"[OSSAPI] {method} {url} with params={params} and data={data}")

        return await super()._request(type_, method, url, params=params, data=data)