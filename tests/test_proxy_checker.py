
import asyncio

import httpx

from src.proxy_checker import check_proxy


def test_proxy_health_success():
    async def test():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200)
        )

        result = await check_proxy(
            "http://127.0.0.1:8080",
            "https://httpbin.org/ip",
            transport=transport,
        )

        assert result["healthy"] is True
        assert result["status_code"] == 200
        assert result["response_time_ms"] >= 0
        assert result["error"] is None

    asyncio.run(test())


def test_proxy_health_failure():
    async def test():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(502)
        )

        result = await check_proxy(
            "http://127.0.0.1:8080",
            "https://httpbin.org/ip",
            transport=transport,
        )

        assert result["healthy"] is False
        assert result["status_code"] == 502

    asyncio.run(test())


def test_proxy_credentials_are_redacted():
    async def test():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200)
        )

        result = await check_proxy(
            "http://user123:secret456@127.0.0.1:8080",
            "https://httpbin.org/ip",
            transport=transport,
        )

        assert "user123" not in result["proxy"]
        assert "secret456" not in result["proxy"]
        assert "***:***@" in result["proxy"]

    asyncio.run(test())
