
import asyncio
import time

import httpx


TIMEOUT = 15


async def check_proxy(proxy_url, health_check_url):
    start_time = time.perf_counter()

    result = {
        "proxy": proxy_url,
        "healthy": False,
        "status_code": None,
        "response_time_ms": None,
        "error": None,
    }

    try:
        async with httpx.AsyncClient(
            proxy=proxy_url,
            timeout=TIMEOUT,
            follow_redirects=True,
        ) as client:

            response = await client.get(
                health_check_url
            )

        elapsed = (
            time.perf_counter() - start_time
        ) * 1000

        result.update({
            "healthy": response.is_success,
            "status_code": response.status_code,
            "response_time_ms": round(
                elapsed, 2
            ),
        })

    except httpx.RequestError as exc:
        result["error"] = str(exc)

    return result


async def check_all_proxies(
    proxies,
    health_check_url,
):
    tasks = [
        check_proxy(proxy, health_check_url)
        for proxy in proxies
    ]

    return await asyncio.gather(*tasks)
