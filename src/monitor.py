
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import httpx

from src.proxy_rotator import ProxyRotator


TIMEOUT = 15
CONCURRENCY = 3
DEFAULT_RESPONSE_TIME_THRESHOLD_MS = 1500


def redact_proxy(proxy_url):
    """Hide proxy username/password before including them in results."""
    if not proxy_url:
        return None

    parts = urlsplit(proxy_url)

    if parts.username is None and parts.password is None:
        return proxy_url

    host = parts.hostname or ""

    if parts.port:
        host = f"{host}:{parts.port}"

    redacted_netloc = f"***:***@{host}"

    return urlunsplit((
        parts.scheme,
        redacted_netloc,
        parts.path,
        parts.query,
        parts.fragment,
    ))


async def check_website(
    url,
    client,
    response_time_threshold_ms=DEFAULT_RESPONSE_TIME_THRESHOLD_MS,
    proxy_url=None,
):
    start_time = datetime.now(timezone.utc)

    result = {
        "url": url,
        "timestamp": start_time.isoformat(),
        "status_code": None,
        "response_time_ms": None,
        "cloudflare": False,
        "challenge_detected": False,
        "outcome": "unknown",
        "error": None,
        "proxy": redact_proxy(proxy_url),
    }

    try:
        response = await client.get(url)

        elapsed = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        headers = response.headers
        body = response.text[:10000].lower()

        is_cloudflare = (
            "cloudflare" in headers.get(
                "server", ""
            ).lower()
            or "cf-ray" in headers
        )

        is_challenge = (
            headers.get(
                "cf-mitigated", ""
            ).lower() == "challenge"
            or "challenge-platform" in body
            or "cf-chl-" in body
        )

        if is_challenge:
            outcome = "cloudflare_challenge"
        elif response.is_success:
            if elapsed > response_time_threshold_ms:
                outcome = "slow"
            else:
                outcome = "reachable"
        else:
            outcome = "http_error"

        result.update({
            "status_code": response.status_code,
            "response_time_ms": round(elapsed, 2),
            "cloudflare": is_cloudflare,
            "challenge_detected": is_challenge,
            "outcome": outcome,
        })

    except httpx.TimeoutException:
        result["outcome"] = "timeout"
        result["error"] = "Request timed out"

    except httpx.RequestError as exc:
        result["outcome"] = "connection_error"

        # Do not expose proxy credentials in error text.
        result["error"] = (
            "Request failed through proxy"
            if proxy_url
            else str(exc)
        )

    return result


async def check_with_proxy_failover(
    url,
    proxies,
    response_time_threshold_ms=DEFAULT_RESPONSE_TIME_THRESHOLD_MS,
):
    """
    Try proxies in order, moving to the next after a
    timeout or connection error.
    """
    if not proxies:
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
        ) as client:
            result = await check_website(
                url,
                client,
                response_time_threshold_ms,
            )
            result["proxy_attempts"] = 0
            return result

    last_result = None

    for attempt_number, proxy_url in enumerate(proxies, start=1):
        async with httpx.AsyncClient(
            proxy=proxy_url,
            timeout=TIMEOUT,
            follow_redirects=True,
        ) as client:
            result = await check_website(
                url,
                client,
                response_time_threshold_ms,
                proxy_url=proxy_url,
            )

        result["proxy_attempts"] = attempt_number
        last_result = result

        # Retry only transport failures.
        if result["outcome"] not in (
            "timeout",
            "connection_error",
        ):
            return result

    return last_result


async def monitor_websites(
    urls,
    response_time_threshold_ms=DEFAULT_RESPONSE_TIME_THRESHOLD_MS,
    proxies=None,
):
    semaphore = asyncio.Semaphore(CONCURRENCY)

    configured_proxies = list(proxies or [])
    proxy_rotator = ProxyRotator(configured_proxies)

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
    ) as direct_client:

        async def limited_check(url):
            async with semaphore:
                first_proxy = proxy_rotator.next_proxy()

                # No configured proxy: use direct monitoring.
                if first_proxy is None:
                    return await check_website(
                        url,
                        direct_client,
                        response_time_threshold_ms,
                    )

                # Round-robin proxy is the first choice.
                # Then try the remaining configured proxies.
                proxy_order = [
                    first_proxy,
                    *[
                        proxy
                        for proxy in configured_proxies
                        if proxy != first_proxy
                    ],
                ]

                return await check_with_proxy_failover(
                    url,
                    proxy_order,
                    response_time_threshold_ms,
                )

        tasks = [
            limited_check(url)
            for url in urls
        ]

        return await asyncio.gather(*tasks)
