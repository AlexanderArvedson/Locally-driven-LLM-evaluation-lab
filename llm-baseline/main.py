import time
import json
import requests
from datetime import datetime, timezone

MODEL = "qwen2.5-coder"
URL = "http://localhost:11434/api/generate"


def call_model(prompt: str):
    start = time.perf_counter()

    try:
        response = requests.post(
            URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
    except requests.exceptions.RequestException as e:
        end = time.perf_counter()
        return {
            "model": MODEL,
            "prompt": prompt,
            "error": True,
            "error_type": "request_exception",
            "error_message": str(e),
            "latency_ms": (end - start) * 1000
        }

    end = time.perf_counter()

    # HTTP-level error
    if response.status_code != 200:
        return {
            "model": MODEL,
            "prompt": prompt,
            "error": True,
            "error_type": "http_error",
            "status_code": response.status_code,
            "body": response.text,
            "latency_ms": (end - start) * 1000
        }

    try:
        data = response.json()
    except ValueError:
        return {
            "model": MODEL,
            "prompt": prompt,
            "error": True,
            "error_type": "invalid_json",
            "raw": response.text,
            "latency_ms": (end - start) * 1000
        }

    output = data.get("response")

    if output is None:
        return {
            "model": MODEL,
            "prompt": prompt,
            "error": True,
            "error_type": "missing_response_field",
            "raw": data,
            "latency_ms": (end - start) * 1000
        }

    return {
        "model": MODEL,
        "prompt": prompt,
        "output": output,
        "error": False,
        "latency_ms": (end - start) * 1000
    }


def log(result):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": result.get("model"),
        "prompt": result.get("prompt"),
        "output": result.get("output"),
        "latency_ms": result.get("latency_ms"),
        "error": result.get("error", False),
        "error_type": result.get("error_type", None)
    }

    with open("logs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":

    prompts = [
        "write a function that checks if a string is a palindrome.",
        "explain recursion in simple terms.",
        "write a python function that sorts a list."
    ]

    for prompt in prompts:
        result = call_model(prompt)
        log(result)
        print("\n--- OUTPUT ---\n")
        print(result.get("output") or result.get("error_type"))