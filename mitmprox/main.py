from mitmproxy import http # type: ignore
from mitmproxy.http import Response

DEVSERVER_DOMAIN = "ripple.moe"

class MyMitmproxy:
    async def request(self, flow: http.HTTPFlow) -> None:
        # TODO: use hosts file, to 127.0.0.1 for c4.example.com and etc
        
        # TODO: Redirect to `localosuserver.com` instead of `*.ppy.sh`
        # Ensures safety of the user's bancho account
        if flow.request.pretty_host.endswith(DEVSERVER_DOMAIN):
            subdomain = flow.request.pretty_host.split(".")[0]
            location = flow.request.url.replace(f"https://{subdomain}.{DEVSERVER_DOMAIN}", f"http://localhost:8000/{subdomain}")
            
            flow.response = Response.make(
                status_code=307,
                headers={"Location": location},
            )
            
addons = [MyMitmproxy()]