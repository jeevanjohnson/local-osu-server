from proxy.usecases import ProxyDomainUseCases
from jays_tools.services import Service, ReadinessSignal


def stop():
    proxy_domain_usecases = ProxyDomainUseCases()
    proxy_domain_usecases.disable_osu_proxy()


def start(readiness_signal: ReadinessSignal):
    proxy_domain_usecases = ProxyDomainUseCases()
    proxy_domain_usecases.enable_osu_proxy("./proxy/mitm.py")
    readiness_signal.set()


def ProxyService() -> Service:
    return Service(
        name="Proxy Service",
        description="Service responsible for setting up a local proxy to intercept osu! web traffic and extract data.",
        start_func=start,
        stop_func=stop,
    )
