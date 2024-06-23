from mitmproxy import http # type: ignore
from mitmproxy.http import Response

class MyMitmproxy:
    async def request(self, flow: http.HTTPFlow) -> None:
        
        # TODO: Redirect to `localosuserver.com` instead of `*.ppy.sh`
        # Ensures safety of the user's bancho account
        if flow.request.pretty_host.endswith(".ppy.sh"):
            subdomain = flow.request.pretty_host.split(".")[0]
            location = flow.request.url.replace(f"https://{subdomain}.ppy.sh", f"http://localhost:8000/{subdomain}")
            
            flow.response = Response.make(
                status_code=307,
                headers={"Location": location},
            )
            
addons = [MyMitmproxy()]