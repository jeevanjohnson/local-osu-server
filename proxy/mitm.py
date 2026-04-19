"""
Purpose/Domain/Concept:
- This file contains the implementation of the proxy server used to redirect the osu! client to the user's local machine.
"""

from mitmproxy import http  # type: ignore
from mitmproxy.http import Response

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import core.usecases.domain.port as port_usecases

OSU_CLIENT_REQUEST_URL = "akatsuki.gg"

""" Architectural Notes: """
# Status codes 301 & 302 are not used since using them would cause the request to turn into a GET request.
# osu! client likes to send POST requests with a body of data so we use 307 to ensure the request method and body are preserved
# during the redirection.
# To avoid any DNS issues, we have to direct our proxy server to listen on a URL that the osu! client will request, which is akatsuki.gg.
# This means that we have to redirect requests from akatsuki.gg to localhost:5001, where our local server will be running.

SUCCESS_MESSAGE_SENT = False

class Proxy:
    # Intercepts all http requests being made on the machine.
    async def request(self, flow: http.HTTPFlow) -> None:
        global SUCCESS_MESSAGE_SENT
        if not SUCCESS_MESSAGE_SENT:
            print("Proxy server is running and intercepting requests!")
            SUCCESS_MESSAGE_SENT = True

        if flow.request.pretty_host.endswith(OSU_CLIENT_REQUEST_URL):
            subdomain = flow.request.pretty_host.split(".")[0]

            port = port_usecases.retrive_port_for("server")
            
            new_location = flow.request.url.replace(
                f"https://{subdomain}.{OSU_CLIENT_REQUEST_URL}",
                f"http://localhost:{port}/{subdomain}",
            )

            flow.response = Response.make(
                status_code=307,
                headers={"Location": new_location},
            )


addons = [Proxy()]
