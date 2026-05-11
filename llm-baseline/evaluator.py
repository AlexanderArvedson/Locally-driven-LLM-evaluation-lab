import json
import os
import argparse
from collections import defaultdict

LOG_DIR = "logs"
METADATA_DIR = "metadata"

# Utility to read JSONL files and yield parsed objects, skipping invalid lines
def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue

# Summarize results from a run log file, computing average latency and success rates per model and category
def summarize(run_log_path):
    stats = {}
    per_model = defaultdict(lambda: {"count": 0, "total_latency": 0.0, "success_count": 0})
    per_category = defaultdict(lambda: {"count": 0, "total_latency": 0.0, "success_count": 0})

    for entry in read_jsonl(run_log_path):
        model = entry.get("model")
        cat = entry.get("category", "unknown")
        latency = entry.get("latency_ms") or 0.0
        success = bool(entry.get("success"))

        per_model[model]["count"] += 1
        per_model[model]["total_latency"] += latency
        if success:
            per_model[model]["success_count"] += 1

        per_category[cat]["count"] += 1
        per_category[cat]["total_latency"] += latency
        if success:
            per_category[cat]["success_count"] += 1

    # compute aggregates
    stats["by_model"] = {}
    for m, v in per_model.items():
        count = v["count"]
        stats["by_model"][m] = {
            "samples": count,
            "avg_latency_ms": (v["total_latency"] / count) if count else None,
            "success_rate": (v["success_count"] / count) if count else None
        }

    stats["by_category"] = {}
    for c, v in per_category.items():
        count = v["count"]
        stats["by_category"][c] = {
            "samples": count,
            "avg_latency_ms": (v["total_latency"] / count) if count else None,
            "success_rate": (v["success_count"] / count) if count else None
        }

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", "-l", help="Path to run jsonl file. If omitted the latest file in logs/ is used.")
    args = parser.parse_args()

    run_log = args.log
    if not run_log:
        # find latest run_*.jsonl in logs/
        if not os.path.isdir(LOG_DIR):
            raise SystemExit("No logs directory found")
        files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.startswith("run_") and f.endswith(".jsonl")]
        if not files:
            raise SystemExit("No run logs found in logs/")
        run_log = max(files, key=os.path.getmtime)

    summary = summarize(run_log)
    print(json.dumps(summary, indent=2))

    # also write summary to metadata if run_id present
    try:
        # try extract run_id from filename
        base = os.path.basename(run_log)
        if base.startswith("run_"):
            run_id = base[len("run_"):-len(".jsonl")]
            out_path = os.path.join(METADATA_DIR, f"summary_{run_id}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
    except Exception:
        pass
