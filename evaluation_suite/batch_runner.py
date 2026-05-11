#!/usr/bin/env python3
"""
Batch compliance measurement framework.
Runs evaluation N times and collects failure mode statistics.
"""

import requests
import time
import json
import sys
from collections import defaultdict
from tasks.task_01.task_01 import TASK_01_PROMPT
from scorer import score_model_output

MODEL = "qwen2.5-coder"
URL = "http://localhost:11434/api/generate"

def run_model(prompt):
    """Run model once and capture output."""
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
    
    return failures if failures else ["no_failures_detected"]


def run_batch(n_runs=10, verbose=True):
    """Run evaluation N times and collect statistics."""
    
    results = []
    failure_modes = defaultdict(int)
    scores = []
    
    print(f"\n{'='*60}")
    print(f"BATCH COMPLIANCE MEASUREMENT: {n_runs} runs")
    print(f"{'='*60}\n")
    
    for i in range(n_runs):
        print(f"[{i+1:2d}/{n_runs}] Running evaluation...", end=" ", flush=True)
        
        run_result = run_model(TASK_01_PROMPT)
        
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
        scores.append(score_val)
        
        # Store full result
        results.append({
            "run": i + 1,
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
    print(f"\nScore distribution:")
    print(f"  Mean score:            {sum(scores) / len(scores):.2f}/10")
    print(f"  Median score:          {sorted(scores)[len(scores)//2]}/10")
    print(f"  Min score:             {min(scores)}/10")
    print(f"  Max score:             {max(scores)}/10")
    print(f"  Std dev:               {calculate_stddev(scores):.2f}")
    
    print(f"\nFailure mode distribution:")
    for mode, count in sorted(failure_modes.items(), key=lambda x: -x[1]):
        pct = (count / (len(results) * 2.5) * 100)  # Normalize by runs * avg failures/run
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
    output_file = "results/batch_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "summary": {
                "total_runs": len(results),
                "compliant_rate": compliance_rate,
                "mean_score": sum(scores) / len(scores) if scores else 0,
                "failure_modes": dict(failure_modes)
            },
            "runs": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return results, failure_modes, scores


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
