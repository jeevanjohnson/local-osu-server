"""
Purpose/Domain/Concept:
- This file contains the implementation of the proxy server used to redirect the osu! client to the user's local machine.
"""

from mitmproxy import http  # type: ignore
from mitmproxy.http import Response

import sys  # noqa
from pathlib import Path  # noqa

sys.path.append(str(Path(__file__).parent.parent))  # noqa

from constants import OsuClient, Ports

""" Architectural Notes: """
# Status codes 301 & 302 are not used since using them would cause the request to turn into a GET request.
# osu! client likes to send POST requests with a body of data so we use 307 to ensure the request method and body are preserved
# during the redirection.
# To avoid any DNS issues, we have to direct our proxy server to listen on a URL that the osu! client will request, which is akatsuki.gg.
# This means that we have to redirect requests from akatsuki.gg to localhost:5001, where our local server will be running.


class Proxy:
    # Intercepts all http requests being made on the machine.
    async def request(self, flow: http.HTTPFlow) -> None:
        if flow.request.pretty_host.endswith(OsuClient.REQUEST_URL):
            subdomain = flow.request.pretty_host.split(".")[0]

            new_location = flow.request.url.replace(
                f"https://{subdomain}.{OsuClient.REQUEST_URL}",
                f"http://localhost:{Ports.SERVER}/{subdomain}",
            )

            flow.response = Response.make(
                status_code=307,
                headers={"Location": new_location},
            )


addons = [Proxy()]
