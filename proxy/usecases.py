from jays_tools.architecture import DomainUseCase
from jays_tools.architecture import Adapters
from proxy.adapters import WindowsProxyAdapter, MitmProxyAdapter


class ProxyAdapters(Adapters):
    windows = WindowsProxyAdapter()
    mitm = MitmProxyAdapter()


class ProxyDomainUseCases(DomainUseCase):
    def __init__(self) -> None:
        self.adapters = ProxyAdapters()
        self.repositories = None
        self.services = None

    def enable_osu_proxy(self, proxy_script_location: str) -> None:
        self.adapters.windows.enable_windows_proxy(
            "http://localhost:8080",
            "*.ppy.sh*"
        )
        self.adapters.mitm.start_middleman_proxy(proxy_script_location)

    def disable_osu_proxy(self) -> None:
        self.adapters.windows.disable_windows_proxy()
        self.adapters.mitm.stop_middle_man_proxy()
