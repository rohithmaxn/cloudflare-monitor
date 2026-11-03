import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from src.monitor import monitor_websites
from src.proxy_checker import check_all_proxies


NAME = "ChatGPT (GPT-6)"

def load_targets():
    config_path = Path("config/targets.json")

    if not config_path.exists():
        raise FileNotFoundError(
            "Missing config/targets.json"
        )

    config = json.loads(
        config_path.read_text(encoding="utf-8")
    )

    targets = config.get("targets")

    if not isinstance(targets, list) or not targets:
        raise ValueError(
            "config/targets.json must contain a non-empty targets list"
        )

    if not all(
        isinstance(url, str) and url.startswith(("http://", "https://"))
        for url in targets
    ):
        raise ValueError(
            "Each target must be a valid HTTP or HTTPS URL"
        )

    return targets

def parse_args():
    parser = argparse.ArgumentParser(
        description="Monitor website availability and response indicators."
    )

    parser.add_argument(
        "--url",
        action="append",
        dest="urls",
        help="URL to monitor. Can be supplied more than once.",
    )

    parser.add_argument(
        "--output",
        default="reports/results.json",
        help="JSON report path. Default: reports/results.json",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Seconds between monitoring runs. Default: 60.",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of monitoring runs. Default: 1.",
    )

    args = parser.parse_args()

    if args.interval < 1:
        parser.error("--interval must be at least 1 second.")

    if args.count < 1:
        parser.error("--count must be at least 1.")

    return args


def load_proxy_config():
    config_path = Path("config/proxies.json")

    if not config_path.exists():
        return {
            "proxies": [],
            "health_check_url": "https://httpbin.org/ip",
        }

    return json.loads(
        config_path.read_text(encoding="utf-8")
    )


async def main():
    args = parse_args()
    targets = args.urls if args.urls else load_targets()

    print(f"Name: {NAME}")
    print(
        f"Today's date: "
        f"{datetime.now().strftime('%Y-%m-%d')}"
    )
    print("-" * 50)

    config = load_proxy_config()

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    history_file = reports_dir / "history.jsonl"

    for run_number in range(1, args.count + 1):
        website_results = await monitor_websites(targets)

        proxy_results = await check_all_proxies(
            config["proxies"],
            config["health_check_url"],
        )

        summary = {
            "reachable": sum(
                result["outcome"] == "reachable"
                for result in website_results
            ),
            "http_errors": sum(
                result["outcome"] == "http_error"
                for result in website_results
            ),
            "request_failures": sum(
                result["outcome"] == "request_error"
                for result in website_results
            ),
            "cloudflare_indicators": sum(
                result["cloudflare"]
                for result in website_results
            ),
            "challenges_detected": sum(
                result["challenge_detected"]
                for result in website_results
            ),
        }

        report = {
            "run_number": run_number,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total_website_checks": len(website_results),
            "total_proxy_checks": len(proxy_results),
            "summary": summary,
            "website_results": website_results,
            "proxy_results": proxy_results,
        }

        output_file.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        with history_file.open(
            "a",
            encoding="utf-8",
        ) as history:
            history.write(json.dumps(report) + "\n")

        print(
            f"Run {run_number}/{args.count}: "
            f"{summary['reachable']} reachable, "
            f"{summary['http_errors']} HTTP errors, "
            f"{summary['request_failures']} request failures"
        )

        if run_number < args.count:
            await asyncio.sleep(args.interval)

    print(f"\nLatest report saved to: {output_file}")
    print(f"Run history appended to: {history_file}")

if __name__ == "__main__":
    asyncio.run(main())