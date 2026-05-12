#!/usr/bin/env python3
"""Batch compliance measurement framework.
Runs evaluation N times and collects failure mode statistics.
"""

import requests
import time
import json
from pathlib import Path
from collections import defaultdict
from evaluation_suite.tasks.task_01.task_01 import TASK_01_PROMPT
from core.models import get_registered_models
from evaluation_suite.scorer import score_model_output
from evaluation_suite.utils import generate_run_id, save_run_results

URL = "http://localhost:11434/api/generate"
RESULTS_DIR = Path(__file__).resolve().parent / "results" / "batch_runs"

def run_model(model, prompt):
    """Run model once and capture output."""
    start = time.perf_counter()
    
    try:
        response = requests.post(
            URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        end = time.perf_counter()
        
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}", "latency_ms": None}
        
        data = response.json()
        return {
            "output": data.get("response"),
            "latency_ms": (end - start) * 1000
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": None}


def analyze_failure_modes(output_text):
    """Categorize the type of failure."""
    failures = []
    
    # Signature failures
    if "def generate_user_report(users)" not in output_text:
        if "def generate_user_report(" in output_text:
            failures.append("signature_parameter_mismatch")
        elif "def " in output_text:
            failures.append("completely_different_name")
        else:
            failures.append("no_function_definition")
    
    # OOP drift
    if "class " in output_text:
        failures.append("class_introduction")
    if "def generate_user_report(self" in output_text:
        failures.append("self_parameter_oop")
    
    # File I/O hallucination
    if "open(" in output_text or ".txt" in output_text or ".csv" in output_text:
        failures.append("file_io_hallucination")
    
    # External dependencies
    if "import datetime" in output_text or "from datetime" in output_text:
        failures.append("external_dependency_datetime")
    if "import " in output_text and "collections" not in output_text and "operator" not in output_text:
        failures.append("suspicious_external_imports")
    
    # Return type issues
    if "return {" in output_text or "return dict" in output_text:
        failures.append("returns_dict_not_string")
    if "return [" in output_text or "return (" in output_text:
        failures.append("returns_non_string_iterable")
    
    # Missing core logic
    if "seen" not in output_text and "set()" not in output_text:
        failures.append("no_deduplication")
    if "sort" not in output_text:
        failures.append("no_sorting")
    if "active" not in output_text or "inactive" not in output_text:
        failures.append("no_active_inactive_separation")
    
    # Return a list of detected failure modes (or a sentinel if none)
    return failures if failures else ["no_failures_detected"]


def run_batch(n_runs=10, verbose=True):
    """Run evaluation N times and collect statistics."""
    
    run_id = generate_run_id()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    results = []
    failure_modes = defaultdict(int)
    scores_by_model = defaultdict(list)
    
    print(f"\n{'='*60}")
    print(f"BATCH COMPLIANCE MEASUREMENT: {n_runs} runs")
    print(f"Run ID: {run_id}")
    print(f"{'='*60}\n")
    
    for i in range(n_runs):
        for model in get_registered_models():
            print(f"[{i+1:2d}/{n_runs}] {model}...", end=" ", flush=True)

            run_result = run_model(model, TASK_01_PROMPT)

            if "error" in run_result:
                print(f"ERROR: {run_result['error']}")
                continue

            score_result = score_model_output(run_result["output"])

            # Analyze failures
            failures = analyze_failure_modes(run_result["output"])
            for failure in failures:
                failure_modes[failure] += 1

            # Collect metrics
            score_val = score_result["score"]
            scores_by_model[model].append(score_val)

            # Store full result
            results.append({
                "run": i + 1,
                "model": model,
                "score": score_val,
                "normalized": score_result["normalized"],
                "is_compliant": score_result["is_compliant"],
                "latency_ms": run_result["latency_ms"],
                "failure_modes": failures,
                "compliance_issues": score_result["compliance_issues"]
            })

            status = "✓ COMPLIANT" if score_result["is_compliant"] else "✗ NON-COMPLIANT"
            print(f"{status} | Score: {score_val:2d}/10 | Failures: {len(failures)}")

            if verbose and failures:
                for failure in failures:
                    print(f"         - {failure}")
    
    # ===== STATISTICS =====
    print(f"\n{'='*60}")
    print("COMPLIANCE STATISTICS")
    print(f"{'='*60}\n")
    
    compliant_count = sum(1 for r in results if r["is_compliant"])
    compliance_rate = (compliant_count / len(results) * 100) if results else 0
    
    print(f"Total runs:              {len(results)}")
    print(f"Compliant outputs:       {compliant_count}/{len(results)} ({compliance_rate:.1f}%)")
    print(f"Non-compliant outputs:   {len(results) - compliant_count}/{len(results)} ({100-compliance_rate:.1f}%)")
    print(f"\nScore distribution by model:")
    for model in get_registered_models():
        model_scores = scores_by_model.get(model, [])
        if not model_scores:
            continue
        print(
            f"  {model:20s} "
            f"mean={sum(model_scores) / len(model_scores):.2f}/10 "
            f"median={sorted(model_scores)[len(model_scores)//2]}/10 "
            f"min={min(model_scores)}/10 "
            f"max={max(model_scores)}/10 "
            f"std={calculate_stddev(model_scores):.2f}"
        )
    
    print(f"\nFailure mode distribution:")
    total_result_count = len(results) if results else 1
    for mode, count in sorted(failure_modes.items(), key=lambda x: -x[1]):
        pct = (count / total_result_count * 100)
        print(f"  {mode:40s} {count:3d} occurrences ({pct:5.1f}%)")
    
    # ===== COMPLIANCE CATEGORIES =====
    print(f"\n{'='*60}")
    print("FAILURE CATEGORIES")
    print(f"{'='*60}\n")
    
    categories = {
        "Signature Issues": ["signature_parameter_mismatch", "completely_different_name", "no_function_definition"],
        "OOP Drift": ["class_introduction", "self_parameter_oop"],
        "Hallucinations": ["file_io_hallucination", "external_dependency_datetime", "suspicious_external_imports"],
        "Type Mismatches": ["returns_dict_not_string", "returns_non_string_iterable"],
        "Missing Logic": ["no_deduplication", "no_sorting", "no_active_inactive_separation"]
    }
    
    for category, modes in categories.items():
        count = sum(failure_modes.get(m, 0) for m in modes)
        print(f"{category:30s}: {count:3d} failures")
    
    # Save detailed results
    output_file = RESULTS_DIR / f"batch_results_{run_id}.json"
    
    batch_data = {
        "summary": {
            "total_runs": len(results),
            "compliant_rate": compliance_rate,
            "registered_models": get_registered_models(),
            "mean_score": (
                sum(score for score_list in scores_by_model.values() for score in score_list)
                / sum(len(score_list) for score_list in scores_by_model.values())
            ) if results else 0,
            "failure_modes": dict(failure_modes)
        },
        "runs": results
    }
    
    save_run_results(run_id, batch_data, str(output_file))
    print(f"\nDetailed results saved to: {output_file}")
    
    # Return collected results, aggregated failure mode counts, and per-model scores
    return results, failure_modes, scores_by_model


def calculate_stddev(values):
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5


if __name__ == "__main__":
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    run_batch(n_runs=n_runs, verbose=True)
