#!/usr/bin/env python3
"""
Basic Azure OpenAI Responses API example.

Usage:
    # Export env vars first if available; .env is only used as fallback.
    python3 hello_azure_openai.py

Config values (from environment variables first, then .env):
    AZURE_API_KEY
  AZURE_OPENAI_ENDPOINT   (default: https://jls.openai.azure.com)
  AZURE_OPENAI_API_VERSION(default: 2025-04-01-preview)
  AZURE_OPENAI_MODEL      (default: gpt-5.4)
"""

import json
import os
import sys
import urllib.error
import urllib.request


def load_dotenv(dotenv_path: str = ".env") -> dict[str, str]:
    """Load key=value pairs from a .env file.

    Supports lines like:
      KEY=value
      KEY="value"
      KEY='value'
    Ignores blank lines and comments starting with '#'.
    """
    values: dict[str, str] = {}
    if not os.path.exists(dotenv_path):
        return values

    with open(dotenv_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                continue

            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
                value = value[1:-1]

            values[key] = value

    return values


def config_value(name: str, dotenv_values: dict[str, str], default: str | None = None) -> str | None:
    """Return env var first, then .env value, then default."""
    return os.getenv(name) or dotenv_values.get(name) or default


def extract_text(response_json: dict) -> str:
    """Best-effort extraction of text from Responses API JSON."""
    output = response_json.get("output", [])
    chunks = []

    for item in output:
        if isinstance(item, dict):
            # Common shape: output_text directly on item
            if isinstance(item.get("output_text"), str):
                chunks.append(item["output_text"])

            # Alternate shape: content array with text entries
            content = item.get("content", [])
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if isinstance(part.get("text"), str):
                        chunks.append(part["text"])
                    elif isinstance(part.get("output_text"), str):
                        chunks.append(part["output_text"])

    if chunks:
        return "\n".join(c for c in chunks if c).strip()

    # Fallback: pretty-print full JSON if text cannot be found
    return json.dumps(response_json, indent=2)


def main() -> int:
    config_names = {
        "AZURE_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_MODEL",
    }
    dotenv_values = load_dotenv() if any(not os.getenv(name) for name in config_names) else {}

    api_key = config_value("AZURE_API_KEY", dotenv_values)
    if not api_key:
        print("Error: AZURE_API_KEY is not set (env or .env).", file=sys.stderr)
        return 1

    endpoint = config_value("AZURE_OPENAI_ENDPOINT", dotenv_values, "https://jls.openai.azure.com")
    api_version = config_value("AZURE_OPENAI_API_VERSION", dotenv_values, "2025-04-01-preview")
    model = config_value("AZURE_OPENAI_MODEL", dotenv_values, "gpt-5.4")

    if not endpoint or not api_version or not model:
        print("Error: Missing required Azure OpenAI configuration.", file=sys.stderr)
        return 1

    endpoint = endpoint.rstrip("/")

    url = f"{endpoint}/openai/responses?api-version={api_version}"

    payload = {
        "input": [
            {
                "role": "user",
                "content": "Hello! Where are you hosted?",
            }
        ],
        "max_output_tokens": 256,
        "model": model,
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_data = response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        details = err.read().decode("utf-8", errors="replace")
        print(f"HTTP {err.code}: {details}", file=sys.stderr)
        return 1
    except urllib.error.URLError as err:
        print(f"Request failed: {err}", file=sys.stderr)
        return 1

    response_json = json.loads(response_data)
    print(extract_text(response_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
