from __future__ import annotations

from typing import Any

from ossapi import OssapiAsync as BaseOssapiAsync
from ossapi.mod import Mod


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

        if (
            isinstance(params, dict)
            and "mods" in params
            and isinstance(params["mods"], int)
        ):
            params = params.copy()
            params["mods"] = self._mods_int_to_array(params["mods"])

        return await super()._request(type_, method, url, params=params, data=data)
