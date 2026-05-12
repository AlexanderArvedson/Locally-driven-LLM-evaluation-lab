# Locally-driven-LLM

Research on locally-run LLM compliance and refactoring capabilities. Measures how well LLMs adhere to constraints when modifying code.

## Quick Start

```bash
# From project root

# Single evaluation
uv run -m evaluation_suite.runner

# Batch with statistics (10 runs)
uv run -m evaluation_suite.batch_runner 10
```

## Structure

```
.
├── evaluation_suite/       # ⭐ Main testing framework
│   ├── runner.py          # Single evaluation
│   ├── batch_runner.py    # Batch runs with stats
│   ├── scorer.py          # Compliance scoring
│   └── tasks/             # Task definitions
├── docker/                # Ollama + model setup
├── llm-baseline/          # Legacy (see README)
└── main.py               # Root entry (if needed)
```

## Evaluation Suite

See [`evaluation_suite/README.md`](evaluation_suite/README.md) for complete documentation.

**Key features:**
- Compliance measurement for constrained refactoring
- Automatic failure mode detection
- Batch statistics and distribution analysis
- JSON output for analysis

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

1. **API Compliance:** Can models maintain function signatures while refactoring?
2. **Structural Drift:** Do models introduce unnecessary OOP/classes?
3. **Input Sensitivity:** How important is concrete code context vs vague instructions?
4. **Hallucination:** Under what conditions do models fabricate logic?
