
import asyncio

import httpx

from src.monitor import check_website


def run_async(coroutine):
    return asyncio.run(coroutine)


def test_monitor_returns_required_fields():
    async def test():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"server": "nginx"},
            )
        )

        async with httpx.AsyncClient(
            transport=transport
        ) as client:
            result = await check_website(
                "https://example.com",
                client,
            )

        required_fields = [
            "url",
            "timestamp",
            "status_code",
            "response_time_ms",
            "cloudflare",
            "challenge_detected",
            "outcome",
            "error",
        ]

        for field in required_fields:
            assert field in result

    run_async(test())


def test_monitor_classifies_http_200():
    async def test():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200)
        )

        async with httpx.AsyncClient(
            transport=transport
        ) as client:
            result = await check_website(
                "https://example.com",
                client,
            )

        assert result["status_code"] == 200
        assert result["outcome"] == "reachable"

    run_async(test())


def test_monitor_classifies_http_404():
    async def test():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(404)
        )

        async with httpx.AsyncClient(
            transport=transport
        ) as client:
            result = await check_website(
                "https://example.com",
                client,
            )

        assert result["status_code"] == 404
        assert result["outcome"] == "http_error"

    run_async(test())


def test_monitor_detects_cloudflare_challenge():
    async def test():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                403,
                headers={
                    "cf-mitigated": "challenge",
                    "server": "cloudflare",
                },
                text="Cloudflare challenge",
            )
        )

        async with httpx.AsyncClient(
            transport=transport
        ) as client:
            result = await check_website(
                "https://example.com",
                client,
            )

        assert result["cloudflare"] is True
        assert result["challenge_detected"] is True
        assert result["outcome"] == (
            "cloudflare_challenge"
        )

    run_async(test())

def test_monitor_classifies_slow_response(monkeypatch):
    from datetime import datetime, timezone, timedelta
    import src.monitor as monitor_module

    async def test():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200)
        )

        start_time = datetime(
            2026, 1, 1, tzinfo=timezone.utc
        )

        times = iter([
            start_time,
            start_time + timedelta(seconds=1.6),
        ])

        monkeypatch.setattr(
            monitor_module,
            "datetime",
            type(
                "MockDatetime",
                (),
                {
                    "now": staticmethod(
                        lambda tz=None: next(times)
                    )
                },
            ),
        )

        async with httpx.AsyncClient(
            transport=transport
        ) as client:
            result = await check_website(
                "https://example.com",
                client,
                response_time_threshold_ms=1500,
            )

        assert result["status_code"] == 200
        assert result["response_time_ms"] == 1600.0
        assert result["outcome"] == "slow"

    run_async(test())
    
def test_monitor_assigns_proxies_round_robin(monkeypatch):
    import src.monitor as monitor_module

    selected_proxies = []

    class FakeResponse:
        status_code = 200
        headers = {}
        text = ""

        @property
        def is_success(self):
            return True

    class FakeAsyncClient:
        def __init__(
            self,
            proxy=None,
            timeout=None,
            follow_redirects=None,
        ):
            self.proxy = proxy

        async def __aenter__(self):
            return self

        async def __aexit__(
            self,
            exc_type,
            exc,
            traceback,
        ):
            return False

        async def get(self, url):
            selected_proxies.append(self.proxy)
            return FakeResponse()

    monkeypatch.setattr(
        monitor_module.httpx,
        "AsyncClient",
        FakeAsyncClient,
    )

    async def test():
        proxies = [
            "http://proxy-a.example:8080",
            "http://proxy-b.example:8080",
        ]

        results = await monitor_module.monitor_websites(
            [
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
            ],
            proxies=proxies,
        )

        assert len(results) == 3
        assert selected_proxies == [
            proxies[0],
            proxies[1],
            proxies[0],
        ]

        assert [
            result["proxy"]
            for result in results
        ] == [
            proxies[0],
            proxies[1],
            proxies[0],
        ]

    run_async(test())    
    
def test_proxy_failover_tries_next_proxy(monkeypatch):
    import src.monitor as monitor_module

    attempts = []

    class FakeResponse:
        status_code = 200
        headers = {}
        text = ""

        @property
        def is_success(self):
            return True

    class FakeAsyncClient:
        def __init__(
            self,
            proxy=None,
            timeout=None,
            follow_redirects=None,
        ):
            self.proxy = proxy

        async def __aenter__(self):
            return self

        async def __aexit__(
            self,
            exc_type,
            exc,
            traceback,
        ):
            return False

        async def get(self, url):
            attempts.append(self.proxy)

            if self.proxy == "http://proxy-a.example:8080":
                raise httpx.ConnectError(
                    "Connection failed",
                    request=httpx.Request("GET", url),
                )

            return FakeResponse()

    monkeypatch.setattr(
        monitor_module.httpx,
        "AsyncClient",
        FakeAsyncClient,
    )

    async def test():
        proxies = [
            "http://proxy-a.example:8080",
            "http://proxy-b.example:8080",
        ]

        result = await monitor_module.check_with_proxy_failover(
            "https://example.com",
            proxies,
        )

        assert result["outcome"] == "reachable"
        assert result["proxy"] == proxies[1]
        assert result["proxy_attempts"] == 2
        assert attempts == proxies

    run_async(test())