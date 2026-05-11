# Evaluation Suite

Compliance measurement framework for evaluating LLM-generated code against task constraints.

## Structure

```
evaluation_suite/
├── models.py         # Registered model list
├── runner.py           # Single evaluation run
├── batch_runner.py     # Multiple runs with statistics
├── scorer.py           # Compliance scoring logic
├── tasks/
│   └── task_01/        # Refactoring + bugfix task
│       ├── task_01.py  # Task prompt and input
│       ├── task_01_spec.json     # Task specification & scoring rules
│       └── task_01_reference.py  # Reference solution
└── results/            # Output directory (gitignored)
```

## Running Evaluations

### Single Evaluation
```bash
python3 runner.py
```

Runs the task once for every registered model and outputs JSON for each model.

### Batch Runs with Statistics
```bash
python3 batch_runner.py 10  # Run 10 evaluations
```

Produces:
- Summary statistics
- Failure mode distribution
- Compliance rate analysis
- Per-model score distribution
- Detailed results in `batch_results.json`

## Scorer Design

The scorer detects **hard constraint violations** (critical):
- ❌ Signature changes (e.g., wrong parameters)
- ❌ Class introduction (OOP drift)
- ❌ Self parameter (method vs function)
- ❌ Return type changes (dict vs string)

And **soft checks** (functional quality):
- ✓ Deduplication logic
- ✓ Sorting compliance
- ✓ Active/inactive separation
- ✓ Input validation

**Compliance threshold:** score ≥ 7/10 AND all hard constraints satisfied

## Task: Refactoring + Bugfix (task_01)

Model receives a buggy function with these intentional bugs:
1. Deduplication using list instead of set
2. String comparison instead of boolean
3. Sorting disabled
4. Escaped newlines instead of .join()
5. Type mismatches (None vs string returns)

**Constraints:**
- Function signature MUST remain unchanged
- Must stay standalone (no classes/OOP)
- Must return string format
- Must fix all bugs

**Research signal:**
Measures model compliance failure under constrained refactoring—how well can LLMs maintain API contracts while fixing logic?

## Output Structure

### Single Run (runner.py)
```json
{
  "model": "qwen2.5-coder",
  "latency_ms": 45000.0,
  "output": "...function code...",
  "score": {
    "score": 9,
    "max_score": 10,
    "normalized": 0.9,
    "compliance_issues": [],
    "is_compliant": true
  }
}
```

### Batch Results (batch_runner.py)
```json
{
  "summary": {
    "total_runs": 10,
    "compliant_rate": 70.0,
    "mean_score": 7.2,
    "failure_modes": {
      "signature_parameter_mismatch": 2,
      "returns_dict_not_string": 1,
      ...
    }
  },
  "runs": [...]
}
```

## Failure Modes Tracked

- **Signature Issues:** parameter mismatch, different names, no function
- **OOP Drift:** class introduction, self parameter
- **Hallucinations:** file I/O, external dependencies
- **Type Mismatches:** dict vs string, non-string iterables
- **Missing Logic:** no dedup, no sorting, no active/inactive separation
