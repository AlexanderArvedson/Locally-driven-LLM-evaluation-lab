import requests
import time
import json
from tasks.task_01.task_01 import TASK_01_PROMPT
from models import REGISTERED_MODELS
from scorer import score_model_output

URL = "http://localhost:11434/api/generate"

def run_model(model, prompt):
    start = time.perf_counter()

    response = requests.post(
        URL,
        json={
            "model": model,
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
    final = []

    for model in REGISTERED_MODELS:
        result = run_model(model, TASK_01_PROMPT)
        score = score_model_output(result["output"])

        final.append({
            "model": model,
            "latency_ms": result["latency_ms"],
            "output": result["output"],
            "score": score
        })

    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    evaluate()