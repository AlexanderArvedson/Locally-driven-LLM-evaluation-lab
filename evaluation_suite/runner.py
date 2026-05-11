import requests
import time
import json
from tasks.task_01.task_01 import TASK_01_PROMPT
from scorer import score_model_output

MODEL = "qwen2.5-coder"
URL = "http://localhost:11434/api/generate"

def run_model(prompt):
    start = time.perf_counter()

    response = requests.post(
        URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    end = time.perf_counter()

    data = response.json()

    return {
        "output": data.get("response"),
        "latency_ms": (end - start) * 1000
    }


def evaluate():
    result = run_model(TASK_01_PROMPT)

    score = score_model_output(result["output"])

    final = {
        "model": MODEL,
        "latency_ms": result["latency_ms"],
        "output": result["output"],
        "score": score
    }

    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    evaluate()