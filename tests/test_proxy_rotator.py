from src.proxy_rotator import ProxyRotator


def test_proxy_rotator_cycles_through_proxies():
    proxies = [
        "http://proxy-a.example:8080",
        "http://proxy-b.example:8080",
    ]

    rotator = ProxyRotator(proxies)

    assert rotator.next_proxy() == proxies[0]
    assert rotator.next_proxy() == proxies[1]
    assert rotator.next_proxy() == proxies[0]


def test_proxy_rotator_returns_none_when_empty():
    rotator = ProxyRotator([])

    assert rotator.next_proxy() is None
    assert rotator.has_proxies() is False