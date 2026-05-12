import requests
import time
import json
from pathlib import Path
from tasks.task_01.task_01 import TASK_01_PROMPT
from models import REGISTERED_MODELS
from scorer import score_model_output
from utils import generate_run_id, save_run_results

URL = "http://localhost:11434/api/generate"
RESULTS_DIR = Path("evaluation_suite/results/singular_runs")

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
    run_id = generate_run_id()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
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

    output_file = RESULTS_DIR / f"runner_{run_id}.json"
    save_run_results(run_id, final, str(output_file))
    
    print(json.dumps(final, indent=2))
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    evaluate()