from __future__ import annotations

from typing import Any

from ossapi import OssapiAsync as BaseOssapiAsync
from ossapi.mod import Mod

import usecases.sessions


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

            if "cursor" in params and "cursor_string" not in params:
                del params["cursor"]

                # Retrive cursor_string from session
                session = await usecases.sessions.require_current_session()
                params["cursor_string"] = session.osu_client.direct_cursor_string

        try:
            self.api_calls += 1
        except AttributeError:
            self.api_calls = 1
        
        print(f"Making API call #{self.api_calls} to {url} with params: {params} and data: {data}")

        return await super()._request(type_, method, url, params=params, data=data)
