
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
