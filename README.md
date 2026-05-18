# Locally-driven-LLM

Deterministic evaluation harness for measuring local/self-hosted LLM performance on software engineering tasks.

**Research Focus:** Measures how well locally-run LLMs (via Ollama) adhere to explicit constraints when modifying code. Evaluates compliance, correctness, and structural stability.

## Quick Start

```bash
# Single task execution
python main.py task_01 qwen2.5-coder

# With iteration control
python main.py task_01 qwen2.5-coder --iterations 3

# Increase model API timeout for slower generations
python main.py task_01 qwen2.5-coder --model-timeout 300

# List available tasks
python main.py --list-tasks

# View recent results
python main.py --list-results
```

## System Architecture

**Execution Pipeline:**
```
Task Load → Workspace Create → Model Context Build → Model Call
     ↓
Output Parse → Patch Apply → Validate (4-stage) → Score → Persist Results
```

**Validation Pipeline (Deterministic Order):**
1. **Syntax Validation** — Parse AST, detect syntax errors
2. **Import Validation** — Resolve imports, detect missing dependencies  
3. **Test Validation** — Execute pytest suite with timeout
4. **Regression Detection** — Reference passes but modified fails?

**Metrics Tracked:**
- `task_success` — Validation pipeline passed
- `verification_passed` — All pytest tests passed
- `regression_detected` — Reference passes but modified fails
- `compliance_score` — Task-specific rule-based scoring (0-10)
- `iterations_required` — Number of attempts until success
- `lines_changed` — Diff-based line count
- `bytes_changed` — Content size delta
- `runtime_seconds` — Total execution time
- `tokens_used` — Estimated token count

## Project Structure

```
.
├── evaluation_suite/
│   ├── runner.py                      ⭐ Main orchestrator
│   ├── task_loader.py                 Task definition loading
│   ├── workspace_manager.py            Workspace isolation
│   ├── validator.py                   4-stage validation pipeline
│   ├── output_parser.py               Model output parsing (raw + JSON)
│   ├── patch_engine.py                Full-file replacement patching
│   ├── scorer.py                      Metrics & compliance scoring
│   ├── result_store.py                Result persistence & artifacts
│   ├── tasks/
│   │   └── task_01/
│   │       ├── template.py            File to be modified
│   │       ├── reference.py           Reference solution
│   │       ├── tests/test_task.py     Pytest validation tests
│   │       └── spec.json              Task metadata & execution config
│   ├── results/                       Execution results (created at runtime)
│   │   └── singular_runs/
│   │       └── run_<uuid>/
│   │           ├── result.json        Complete execution result
│   │           └── artifacts/         Modified files & reports
│   └── README.md                      Detailed documentation
│
├── docker/                            Ollama setup
├── core/                              Model registry & config
├── main.py                            CLI entry point
└── pyproject.toml                     Dependencies
```

## Task Format

Each task follows a standardized structure:

```
tasks/
  <task_id>/
    template.py              ← File model will modify (buggy implementation)
    reference.py             ← Reference solution (for regression detection)
    tests/
      test_task.py           ← Pytest validation suite (author-written)
      __init__.py
    spec.json                ← Task metadata & scoring rules
```

**Example spec.json:**
```json
{
  "task_id": "task_01",
  "name": "User report refactoring + bugfix",
  "difficulty": "easy-medium",
  "workflow": "bugfix",
  "language": "python",
  "entry_file": "template.py",
  "execution_config": {
    "max_iterations": 3,
    "timeout_seconds": 60,
    "validation_order": ["syntax", "imports", "tests"]
  },
  "evaluation": {
    "method": "rule_based_compliance",
    "scoring_rules": { ... }
  }
}
```

## Workspace Isolation

Each execution creates an isolated per-run workspace:

```
workspace/
  run_<uuid>/
    task/
      template.py              ← Modified by model (copy from task)
      tests/                   ← Pytest tests (copy from task)
      spec.json
    reference.py               ← For regression detection
```

**Key benefits:**
- Original task files never modified
- Complete run inspection for debugging
- Full artifact preservation
- Reproducible execution

## Model Integration

Currently supports **Ollama** API:

```bash
# Start Ollama with models
cd docker
docker compose up

# Expected models
- qwen2.5-coder
- llama3
- mistral
```

Model output supports both formats:
- **Raw code:** Plain Python code (auto-detected)
- **JSON wrapper:** `{"file_path": "...", "content": "..."}`

Parser auto-detects format; Markdown code blocks also supported.

## Iteration & Retry Logic

Tasks support iterative refinement:

```
Iteration 1: Model attempts task
  → If validation passes → SUCCESS
  → If validation fails → Continue

Iteration 2: Model attempts again with same/extended context
  → If validation passes → SUCCESS
  → If validation fails → Continue

Iteration 3: Final attempt (max_iterations = 3)
  → Result regardless of success
```

Metrics include `iterations_required` to track retry count.

## Result Persistence

Each execution persists complete results:

**result.json structure:**
```json
{
  "run_id": "uuid",
  "timestamp": "2026-05-15T...",
  "task_id": "task_01",
  "model_name": "qwen2.5-coder",
  "execution_attempts": [ ... ],
  "scoring": {
    "task_success": true,
    "verification_passed": true,
    "regression_detected": false,
    "compliance_score": 9,
    "iterations_required": 2,
    "lines_changed": 14,
    "runtime_seconds": 38.4,
    "tokens_used": 5120
  },
  "artifacts": { ... }
}
```

## Running Tests

```bash
# Run validation test suite for task_01
pytest evaluation_suite/tasks/task_01/tests/ -v

# Run system tests (when available)
pytest tests/ -v
```

## Adding New Tasks

1. Create `evaluation_suite/tasks/new_task/` directory
2. Add `template.py` (file to modify)
3. Add `reference.py` (reference solution)
4. Add `tests/test_task.py` (pytest validation)
5. Add `spec.json` (metadata)

```bash
# Verify structure
python main.py --list-tasks
```

The runner will automatically discover and load new tasks.

## Development Notes

**Design Principles:**
- ✓ Deterministic execution (fixed validation order, explicit control flow)
- ✓ Workflow-oriented (linear pipeline, no autonomous loops)
- ✓ Reproducible (artifacts preserved, hashes tracked, full logs)
- ✓ Simple (no agent frameworks, no complex orchestration)
- ✓ Extensible (multi-task ready, modular design)
- ✓ Measurable (granular metrics, explicit failure categories)

**Not Included (By Design):**
- ✗ Multi-agent systems
- ✗ Recursive planners
- ✗ Autonomous reasoning loops
- ✗ Graph-based orchestration
- ✗ Database layer (filesystem JSON)
- ✗ Parallel batch execution

These can be added incrementally after the system stabilizes.

## Structure

```
.
├── evaluation_suite/       # Main testing framework
│   ├── runner.py          # Single task execution 
│   ├── batch_runner.py    # Batch runs with stats
│   ├── scorer.py          # Compliance scoring
│   └── tasks/             # Task definitions
├── docker/                # Ollama + model setup
├── core/                  # Model registry & config
└── main.py               # CLI entry point
```

## Evaluation Suite

See [`evaluation_suite/README.md`](evaluation_suite/README.md) for complete documentation.

**Key features:**
- Deterministic validation pipeline (4 stages)
- Workspace isolation per execution
- Full artifact preservation
- Rule-based compliance scoring
- Regression detection
- Comprehensive metrics tracking

## Models

Requires Ollama running locally (http://localhost:11434):

```bash
cd docker
docker compose up --build
```

Currently tested models:
- `qwen2.5-coder` (7.6B, Q4_K_M)
- `llama3` (8B, Q4_0)
- `mistral` (7.2B, Q4_K_M)

## Research Questions

1. **Constraint Adherence:** Can models maintain function signatures while refactoring?
2. **Structural Stability:** Do models introduce unnecessary OOP/classes despite constraints?
3. **Context Sensitivity:** Impact of concrete code vs. abstract instructions?
4. **Correctness:** How often does the generated code pass validation tests?
5. **Reliability:** Consistency across iterations and model variants?
