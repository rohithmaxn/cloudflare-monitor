# Cloudflare Monitor

An asynchronous Python website monitoring project that checks website availability, response times, HTTP errors, Cloudflare indicators, and proxy health. It supports round-robin proxy selection and exports structured JSON reports.

## Features

- Async website monitoring using HTTPX
- Concurrent checks with a configurable concurrency limit
- Response-time threshold classification
- HTTP status, timeout, and connection-error handling
- Cloudflare indicator and challenge detection
- Proxy health checks
- Round-robin proxy selection for configured proxies
- JSON reports and JSONL run history
- Automated tests using pytest and mocked HTTP responses

## Important limitation

This project identifies Cloudflare-related response indicators and challenge pages. It does **not** solve or bypass Cloudflare challenges.

Proxy rotation is intended for authorized monitoring and testing. Use only websites and proxy services you are authorized to access.

## Requirements

- Python 3.14.3 (development environment)
- HTTPX
- pytest

## Project structure

```text
cloudflare-monitor/
├── config/
│   ├── targets.json
│   └── proxies.json
├── reports/
│   ├── results.json
│   └── history.jsonl
├── src/
│   ├── monitor.py
│   ├── proxy_checker.py
│   └── proxy_rotator.py
├── tests/
│   ├── test_monitor.py
│   ├── test_proxy_checker.py
│   ├── test_proxy_rotator.py
│   └── test_runner.py
├── run_monitor.py
├── pytest.ini
├── .gitignore
└── README.md
```

## Architecture

```mermaid
flowchart TD
    A["config/targets.json"] --> B["run_monitor.py"]
    C["config/proxies.json"] --> B

    B --> D["Async Website Monitor"]
    B --> E["Proxy Health Checker"]

    D --> F["Proxy Rotator"]
    F --> G["HTTPX Requests"]
    G --> H["Response Classification"]

    E --> I["Proxy Health Results"]
    H --> J["Structured JSON Report"]

    I --> J
    J --> K["reports/results.json"]
    J --> L["reports/history.jsonl"]

    M["pytest Tests"] --> N["GitHub Actions CI"]


### Example report

The following is an illustrative report showing a reachable website and an HTTP error. Actual response times and timestamps will vary.

```json
{
  "run_number": 1,
  "generated_at": "2026-11-03T10:00:00+00:00",
  "total_website_checks": 2,
  "total_proxy_checks": 0,
  "configured_proxy_count": 0,
  "proxy_rotation_enabled": false,
  "summary": {
    "reachable": 1,
    "slow": 0,
    "http_errors": 1,
    "request_failures": 0,
    "cloudflare_indicators": 0,
    "challenges_detected": 0
  },
  "website_results": [
    {
      "url": "https://example.com",
      "timestamp": "2026-11-03T10:00:00+00:00",
      "status_code": 200,
      "response_time_ms": 187.0,
      "cloudflare": false,
      "challenge_detected": false,
      "outcome": "reachable",
      "error": null,
      "proxy": null
    },
    {
      "url": "https://httpbin.org/status/404",
      "timestamp": "2026-11-03T10:00:00+00:00",
      "status_code": 404,
      "response_time_ms": 789.0,
      "cloudflare": false,
      "challenge_detected": false,
      "outcome": "http_error",
      "error": null,
      "proxy": null
    }
  ],
  "proxy_results": []
}
```

## Setup

Run these commands in PowerShell from the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install httpx pytest
```

## Configuration

### Website targets

Edit `config/targets.json`:

```json
{
  "targets": [
    "https://example.com",
    "https://httpbin.org/status/200",
    "https://httpbin.org/status/404"
  ],
  "response_time_threshold_ms": 1500
}
```

The threshold is measured in milliseconds. A successful response exceeding the threshold is classified as `slow`.

### Proxy configuration

Edit `config/proxies.json`:

```json
{
  "proxies": [],
  "health_check_url": "https://httpbin.org/ip"
}
```

Add proxy URLs to the `proxies` list only when you have authorized proxy endpoints available.

Example format using placeholders:

```json
{
  "proxies": [
    "http://proxy-a.example:8080",
    "http://proxy-b.example:8080"
  ],
  "health_check_url": "https://httpbin.org/ip"
}
```

Do not commit real proxy credentials or secrets to a public repository.

## Run the monitor

Run once using the configured targets:

```powershell
python run_monitor.py
```

Monitor a specific URL:

```powershell
python run_monitor.py --url https://example.com
```

Monitor multiple URLs:

```powershell
python run_monitor.py --url https://example.com --url https://httpbin.org/status/200
```

Set a custom report path:

```powershell
python run_monitor.py --output reports/custom-results.json
```

Run repeatedly:

```powershell
python run_monitor.py --interval 60 --count 5
```

This performs five monitoring runs with a 60-second interval between runs.

## JSON report

The latest report is written to:

```text
reports/results.json
```

Run history is appended to:

```text
reports/history.jsonl
```

The report includes:

- Run number and generation timestamp
- Total website and proxy checks
- Configured proxy count and rotation status
- Summary counts
- Individual website results
- Individual proxy health results

Website outcomes include:

| Outcome | Meaning |
|---|---|
| `reachable` | Successful response within the threshold |
| `slow` | Successful response exceeded the threshold |
| `http_error` | HTTP response was not successful |
| `timeout` | Request timed out |
| `connection_error` | Request failed due to a connection error |
| `cloudflare_challenge` | A Cloudflare challenge indicator was detected |

Cloudflare indicators and challenge detection are reported separately from ordinary reachability.

## Run tests

Run the complete test suite:

```powershell
pytest -v
```

The test suite uses mocked HTTP responses for deterministic checks. It does not require live proxy services.

## Current test coverage

- Required monitoring result fields
- HTTP 200 and HTTP 404 classification
- Cloudflare challenge indicator detection
- Slow-response classification
- Proxy round-robin selection
- Empty proxy configuration behavior
- Proxy health-check behavior
- Target configuration validation

## Example summary

```text
Run 1/1: 2 reachable, 0 slow, 1 HTTP errors, 0 request failures

Latest report saved to: reports\results.json
Run history appended to: reports\history.jsonl
```

## Future improvements

- Retry policies with configurable backoff
- Proxy failure handling and automatic exclusion of unhealthy proxies
- Monitoring dashboard
- Historical response-time charts
- CI pipeline for automated test execution
- Alerting for outages and response-time thresholds

## Author

Python asynchronous monitoring project built as a practical automation and quality-engineering portfolio project.
