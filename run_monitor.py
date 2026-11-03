
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from src.monitor import monitor_websites


NAME = "ChatGPT (GPT-6)"

TARGETS = [
    "https://example.com",
    "https://httpbin.org/status/200",
    "https://httpbin.org/status/404",
]


async def main():
    print(f"Name: {NAME}")
    print(
        f"Today's date: "
        f"{datetime.now().strftime('%Y-%m-%d')}"
    )
    print("-" * 50)

    results = await monitor_websites(TARGETS)

    report = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_checks": len(results),
        "results": results,
    }

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    output_file = reports_dir / "results.json"

    output_file.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
