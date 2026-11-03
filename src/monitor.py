
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import httpx

from src.proxy_rotator import ProxyRotator


TIMEOUT = 15
CONCURRENCY = 3
DEFAULT_RESPONSE_TIME_THRESHOLD_MS = 1500


def redact_proxy(proxy_url):
    """Hide proxy username/password before including it in results."""
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

        # Avoid accidentally exposing proxy credentials in error text.
        result["error"] = (
            "Request failed through proxy"
            if proxy_url
            else str(exc)
        )

    return result


async def monitor_websites(
    urls,
    response_time_threshold_ms=DEFAULT_RESPONSE_TIME_THRESHOLD_MS,
    proxies=None,
):
    semaphore = asyncio.Semaphore(CONCURRENCY)
    proxy_rotator = ProxyRotator(proxies or [])

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
    ) as direct_client:

        async def limited_check(url):
            async with semaphore:
                proxy_url = proxy_rotator.next_proxy()

                if proxy_url is None:
                    return await check_website(
                        url,
                        direct_client,
                        response_time_threshold_ms,
                    )

                async with httpx.AsyncClient(
                    proxy=proxy_url,
                    timeout=TIMEOUT,
                    follow_redirects=True,
                ) as proxy_client:
                    return await check_website(
                        url,
                        proxy_client,
                        response_time_threshold_ms,
                        proxy_url=proxy_url,
                    )

        tasks = [
            limited_check(url)
            for url in urls
        ]

        return await asyncio.gather(*tasks)
