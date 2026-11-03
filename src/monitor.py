
import httpx
from datetime import datetime, timezone


def check_website(url):
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
    }

    try:
        response = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
        )

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
            outcome = "reachable"
        else:
            outcome = "http_error"

        result.update({
            "status_code": response.status_code,
            "response_time_ms": round(
                elapsed, 2
            ),
            "cloudflare": is_cloudflare,
            "challenge_detected": is_challenge,
            "outcome": outcome,
        })

    except httpx.TimeoutException:
        result["outcome"] = "timeout"
        result["error"] = "Request timed out"

    except httpx.RequestError as exc:
        result["outcome"] = "connection_error"
        result["error"] = str(exc)

    return result
