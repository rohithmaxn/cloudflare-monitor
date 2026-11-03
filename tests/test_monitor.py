
from src.monitor import check_website


def test_check_website_returns_dictionary():
    result = check_website(
        "https://example.com"
    )

    assert isinstance(result, dict)


def test_check_website_has_required_fields():
    result = check_website(
        "https://example.com"
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
