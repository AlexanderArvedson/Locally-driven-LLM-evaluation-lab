import time
import json
import requests
import platform
import os
from datetime import datetime, timezone
import uuid
import glob
from shared_paths import LOG_DIR, METADATA_DIR

# model configurations
MODELS = [
    "qwen2.5-coder",
    "llama3"
]

# API endpoint for model inference
URL = "http://localhost:11434/api/generate"

# ----------------------------
# System metadata
# ----------------------------

# Collect system information for metadata logging
def get_system_info():
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count()
    }

# Write system and run metadata to a JSON file for later reference
def write_system_metadata(run_id: str):
    os.makedirs(METADATA_DIR, exist_ok=True)
    metadata = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models": MODELS,
        "system": get_system_info()
    }

    path = os.path.join(METADATA_DIR, f"run_{run_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


# ----------------------------
# Model inference
# ----------------------------

# Call the model API and return structured result including latency and error info
def call_model(model: str, prompt: str):
    start = time.perf_counter()

    try:
        response = requests.post(
            URL,
            json={
                "model": MODELS if isinstance(model, list) else model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
    except requests.exceptions.RequestException as e:
        end = time.perf_counter()
        return {
            "model": model,
            "prompt": prompt,
            "error": True,
            "error_type": "request_exception",
            "error_message": str(e),
            "latency_ms": (end - start) * 1000
        }

    end = time.perf_counter()

    # HTTP error
    if response.status_code != 200:
        return {
            "model": model,
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
            "model": model,
            "prompt": prompt,
            "error": True,
            "error_type": "invalid_json",
            "raw": response.text,
            "latency_ms": (end - start) * 1000
        }

    output = data.get("response")

    if output is None:
        return {
            "model": model,
            "prompt": prompt,
            "error": True,
            "error_type": "missing_response_field",
            "raw": data,
            "latency_ms": (end - start) * 1000
        }

    return {
        "model": model,
        "prompt": prompt,
        "output": output,
        "error": False,
        "latency_ms": (end - start) * 1000
    }


# ----------------------------
# Logging
# ----------------------------

# (legacy single-arg log removed; use run-scoped `log(result, run_id, run_log_path)`)

# Summarize results from a run log file, computing average latency and success rates per model and category
def log(result, run_id: str, run_log_path: str):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "model": result.get("model"),
        "category": result.get("category"),
        "prompt": result.get("prompt"),
        "output": result.get("output"),
        "latency_ms": result.get("latency_ms"),
        "error": result.get("error", False),
        "error_type": result.get("error_type", None),
        "success": result.get("success", None)
    }

    with open(run_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# fetch the prompts from the prompts/ directory, supporting both single JSON objects and lists of objects, each with 'category' and 'prompt' fields
def load_prompts(prompt_dir: str = "prompts"):
    tasks = []
    pattern = os.path.join(prompt_dir, "*.json")
    for path in glob.glob(pattern):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Expect either a list or a single object
                if isinstance(data, list):
                    for item in data:
                        tasks.append(item)
                elif isinstance(data, dict):
                    # If dict with 'tasks' key
                    if "tasks" in data and isinstance(data["tasks"], list):
                        tasks.extend(data["tasks"])
                    else:
                        tasks.append(data)
        except Exception:
            continue
    return tasks

# Heuristic success criteria based on category and output content (can be refined per category)
def heuristic_success(category: str, output: object | None):
    if output is None:
        return False
    try:
        out = output if isinstance(output, str) else str(output)
    except Exception:
        return False

    if category == "code_generation":
        return ("```" in out) or ("def " in out) or ("class " in out)
    # simple fallback: non-empty answer
    return len(out.strip()) > 0


# ----------------------------
# Main experiment loop
# ----------------------------

if __name__ == "__main__":
    # create run id and dirs
    run_id = uuid.uuid4().hex
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)

    # write run metadata
    write_system_metadata(run_id)

    # prepare run-specific log path
    run_log_path = os.path.join(LOG_DIR, f"run_{run_id}.jsonl")

    # load prompts from prompts/ (each item should include 'category' and 'prompt')
    prompts = load_prompts()
    if not prompts:
        # fallback to the original inline prompts (category unknown)
        prompts = [
            {"category": "unknown", "prompt": "write a function that checks if a string is a palindrome."},
            {"category": "explanation", "prompt": "explain recursion in simple terms."},
            {"category": "code_generation", "prompt": "write a python function that sorts a list."}
        ]

    for task in prompts:
        prompt_text = task.get("prompt")
        if not isinstance(prompt_text, str):
            continue

        category_value = task.get("category", "unknown")
        category = category_value if isinstance(category_value, str) else "unknown"

        for model in MODELS:
            result = call_model(model, prompt_text)
            # attach category and compute simple success heuristic
            result["category"] = category
            result["run_id"] = run_id
            if not result.get("error", False):
                result["success"] = heuristic_success(category, result.get("output"))
            else:
                result["success"] = False

            log(result, run_id, run_log_path)

            print(f"\n--- OUTPUT ({model}) ---\n")
            print(result.get("output") or result.get("error_type"))