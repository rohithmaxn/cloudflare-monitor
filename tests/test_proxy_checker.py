
import asyncio

import httpx

from src.proxy_checker import check_proxy


def test_proxy_checker_returns_required_fields():
    async def test():
        result = await check_proxy(
            "http://127.0.0.1:8080",
            "https://httpbin.org/ip",
        )

        required_fields = [
            "proxy",
            "healthy",
            "status_code",
            "response_time_ms",
            "error",
        ]

        for field in required_fields:
            assert field in result

    asyncio.run(test())
