"""
Main task execution runner.

Orchestrates the complete evaluation pipeline:
1. Load task definition
2. Create isolated workspace
3. Build model context
4. Call model API (Ollama)
5. Parse output
6. Apply modifications
7. Validate (syntax → imports → tests → regression)
8. Score result
9. Persist results
10. Handle iteration/retry

Supports iteration: model gets multiple attempts if validation fails.
"""

import uuid
import time
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

from loguru import logger
from pydantic import BaseModel, Field

from .task_loader import TaskLoader
from .workspace_manager import WorkspaceManager, IsolatedWorkspace
from .validator import TemplateValidator
from .output_parser import OutputParser
from .patch_engine import PatchEngine
from .scorer import TaskScorer, ScoringResult
from .result_store import ResultStore, ExecutionResult, ExecutionAttempt, RunArtifacts

# Ollama API configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"


class ExecutionContext(BaseModel):
    """Context for a task execution run"""
    run_id: str = Field(description="Unique run UUID")
    task_id: str
    model_name: str
    workspace: Optional[IsolatedWorkspace] = None
    attempts: list[ExecutionAttempt] = Field(default_factory=list)
    final_iteration: int = 0
    start_time: float = 0.0
    
    class Config:
        arbitrary_types_allowed = True


class TaskRunner:
    """
    Execute tasks with full evaluation pipeline.
    
    Implements:
    - Task loading and validation
    - Workspace isolation
    - Iteration/retry logic
    - Model API integration
    - Complete validation pipeline
    - Scoring and result persistence
    """

    def __init__(
        self,
        tasks_base_dir: Optional[Path] = None,
        workspace_base_dir: Optional[Path] = None,
        results_base_dir: Optional[Path] = None,
        api_endpoint: str = OLLAMA_API_URL
    ):
        """
        Initialize task runner.
        
        Args:
            tasks_base_dir: Tasks directory (default: evaluation_suite/tasks)
            workspace_base_dir: Workspace directory (default: workspace)
            results_base_dir: Results directory (default: results/singular_runs)
            api_endpoint: Ollama API endpoint
        """
        self.task_loader = TaskLoader(tasks_base_dir)
        self.workspace_manager = WorkspaceManager(workspace_base_dir)
        self.result_store = ResultStore(results_base_dir)
        self.validator = TemplateValidator()
        self.api_endpoint = api_endpoint
        
        logger.info(f"TaskRunner initialized")
        logger.info(f"  API endpoint: {self.api_endpoint}")
        logger.info(f"  Tasks: {self.task_loader.tasks_base_dir}")
        logger.info(f"  Workspace: {self.workspace_manager.workspace_base}")
        logger.info(f"  Results: {self.result_store.results_base}")

    def run_task(
        self,
        task_id: str,
        model_name: str,
        max_iterations: Optional[int] = None
    ) -> ExecutionContext:
        """
        Execute task with full pipeline.
        
        Implements retry logic: runs up to max_iterations times, stopping
        if validation passes or max iterations reached.
        
        Args:
            task_id: Task identifier (e.g., "task_01")
            model_name: Model to use (e.g., "qwen2.5-coder")
            max_iterations: Max attempts (default: from task spec)
            
        Returns:
            ExecutionContext with results and attempt history
        """
        run_id = str(uuid.uuid4())
        logger.info(f"═" * 60)
        logger.info(f"Starting task execution: {task_id}")
        logger.info(f"  Run ID: {run_id}")
        logger.info(f"  Model: {model_name}")
        logger.info(f"═" * 60)
        
        # Load task
        try:
            task = self.task_loader.load_task(task_id)
            logger.info(f"✓ Task loaded: {task.metadata.name}")
        except Exception as e:
            logger.error(f"Failed to load task: {str(e)}")
            raise
        
        # Determine max iterations
        if max_iterations is None:
            max_iterations = task.max_iterations
        
        # Create execution context
        ctx = ExecutionContext(
            run_id=run_id,
            task_id=task_id,
            model_name=model_name,
            start_time=time.time()
        )
        
        # Create isolated workspace
        try:
            ctx.workspace = self.workspace_manager.create_workspace(task.task_root)
            logger.info(f"✓ Workspace created: {ctx.workspace.workspace_id}")
        except Exception as e:
            logger.error(f"Failed to create workspace: {str(e)}")
            raise
        
        # Execution loop with retry logic
        for iteration in range(1, max_iterations + 1):
            logger.info(f"\n{'─' * 60}")
            logger.info(f"Iteration {iteration}/{max_iterations}")
            logger.info(f"{'─' * 60}")
            
            # Execute single iteration
            attempt = self._execute_iteration(ctx, task, iteration)
            ctx.attempts.append(attempt)
            ctx.final_iteration = iteration
            
            # Check success
            if attempt.success:
                logger.info(f"✓ Validation passed on iteration {iteration}")
                break
            elif iteration < max_iterations:
                logger.info(f"⚠ Validation failed, retrying...")
            else:
                logger.warning(f"✗ Max iterations reached, task failed")
        
        # Score execution
        total_runtime = time.time() - ctx.start_time
        
        try:
            scoring_result = self._score_execution(ctx, task, total_runtime)
            logger.info(f"✓ Scoring complete")
        except Exception as e:
            logger.error(f"Scoring error: {str(e)}")
            raise
        
        # Persist results
        try:
            execution_result = ExecutionResult(
                run_id=run_id,
                timestamp=datetime.utcnow().isoformat(),
                task_id=task.task_id,
                task_name=task.metadata.name,
                model_name=model_name,
                execution_attempts=ctx.attempts,
                scoring=scoring_result,
                artifacts=RunArtifacts(run_id=run_id)
            )
            
            self.result_store.save_result(
                run_id,
                execution_result,
                ctx.workspace,
                task
            )
            logger.info(f"✓ Results persisted")
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")
            raise
        
        logger.info(f"\n{'═' * 60}")
        logger.info(f"Execution complete")
        logger.info(f"  Run ID: {run_id}")
        logger.info(f"  Success: {scoring_result.task_success}")
        logger.info(f"  Iterations: {ctx.final_iteration}/{max_iterations}")
        logger.info(f"  Compliance Score: {scoring_result.compliance_score}/10")
        logger.info(f"  Runtime: {total_runtime:.2f}s")
        logger.info(f"═" * 60 + "\n")
        
        return ctx

    def _execute_iteration(
        self,
        ctx: ExecutionContext,
        task,
        iteration: int
    ) -> ExecutionAttempt:
        """
        Execute single iteration of task.
        
        Steps:
        1. Build model context
        2. Call model
        3. Parse output
        4. Apply modifications
        5. Validate
        
        Args:
            ctx: Execution context
            task: Task definition
            iteration: Current iteration number
            
        Returns:
            ExecutionAttempt with results
        """
        iteration_start = time.time()
        
        # Step 1: Build model context
        logger.info("Step 1: Building model context")
        prompt = self._build_model_prompt(task, ctx.workspace, iteration)
        logger.info(f"  Prompt length: {len(prompt)} characters")
        
        # Step 2: Call model
        logger.info("Step 2: Calling model API")
        try:
            model_output = self._call_model(
                prompt,
                ctx.model_name,
                timeout_seconds=task.timeout_seconds
            )
            logger.info(f"  Response length: {len(model_output)} characters")
        except Exception as e:
            logger.error(f"Model API error: {str(e)}")
            raise
        
        # Step 3: Parse output
        logger.info("Step 3: Parsing model output")
        parsed_output = OutputParser.parse(model_output)
        logger.info(f"  Format detected: {parsed_output.format_detected}")
        
        if not parsed_output.success:
            logger.error(f"  Parse error: {parsed_output.extraction_error}")
        
        # Step 4: Apply modifications
        logger.info("Step 4: Applying modifications")
        patch_result = PatchEngine.apply_modification(
            parsed_output,
            ctx.workspace.workspace_root,
            "task/template.py"
        )
        
        if not patch_result.success:
            logger.error(f"  Patch error: {patch_result.error}")
        else:
            logger.info(f"  ✓ Modifications applied: {patch_result.lines_changed} lines changed")
        
        # Step 5: Validate
        logger.info("Step 5: Running validation pipeline")
        validation_report = self.validator.run_full_validation(
            ctx.workspace.workspace_root,
            template_file="task/template.py",
            tests_dir="task/tests",
            reference_file="reference.py"
        )
        
        # Determine attempt success
        attempt_success = validation_report.overall_passed
        
        iteration_duration = time.time() - iteration_start
        
        attempt = ExecutionAttempt(
            iteration=iteration,
            timestamp=datetime.utcnow().isoformat(),
            model_output_raw=model_output,
            duration_seconds=iteration_duration,
            validation_report=validation_report,
            success=attempt_success
        )
        
        return attempt

    def _build_model_prompt(self, task, workspace: IsolatedWorkspace, iteration: int) -> str:
        """
        Build model input prompt from task definition.
        
        Args:
            task: Task definition
            workspace: Isolated workspace with template
            iteration: Current iteration number
            
        Returns:
            Complete prompt for model
        """
        # Read current template
        try:
            with open(workspace.template_file, "r", encoding="utf-8") as f:
                current_template = f.read()
        except Exception as e:
            logger.error(f"Error reading template: {str(e)}")
            current_template = ""
        
        # Read reference solution for later iterations
        reference_solution = ""
        if iteration > 1 and workspace.reference_file.exists():
            try:
                with open(workspace.reference_file, "r", encoding="utf-8") as f:
                    reference_solution = f.read()
            except Exception as e:
                logger.warning(f"Could not read reference: {str(e)}")
        
        # Build prompt from task spec
        model_instructions = task.spec.model_instructions
        constraints = "\n".join(f"  - {c}" for c in model_instructions.get("constraints", []))
        rules = "\n".join(f"  - {r}" for r in model_instructions.get("rules", []))
        
        prompt = f"""You are an expert Python developer. Your task is to refactor and fix code.

TASK: {task.metadata.name}
OBJECTIVE: {model_instructions.get('objective', '')}

CONSTRAINTS:
{constraints}

RULES:
{rules}

CURRENT CODE:
```python
{current_template}
```

EXPECTED BEHAVIOR:
{task.spec.expected_behavior}

{f'REFERENCE SOLUTION (for iteration {iteration}):' + chr(10) + '```python' + chr(10) + reference_solution + chr(10) + '```' + chr(10) if reference_solution else ''}

OUTPUT INSTRUCTIONS:
1. Return ONLY the complete, corrected Python code.
2. Wrap your code in ```python``` markers.
3. Do NOT include any explanation or comments outside the code block.
4. Ensure the code is syntactically correct and passes all requirements.
"""
        
        return prompt

    def _call_model(self, prompt: str, model_name: str, timeout_seconds: int = 60) -> str:
        """
        Call model via Ollama API.
        
        Args:
            prompt: Input prompt
            model_name: Model identifier
            timeout_seconds: Request timeout
            
        Returns:
            Model response text
        """
        try:
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=timeout_seconds
            )
            
            response.raise_for_status()
            data = response.json()
            model_output = data.get("response", "")
            
            if not model_output:
                logger.warning("Empty response from model")
            
            return model_output
            
        except requests.exceptions.Timeout:
            logger.error(f"Model API timeout after {timeout_seconds}s")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to model API at {self.api_endpoint}")
            raise
        except Exception as e:
            logger.error(f"Model API error: {str(e)}")
            raise

    def _score_execution(self, ctx: ExecutionContext, task, total_runtime: float) -> ScoringResult:
        """
        Score complete execution.
        
        Args:
            ctx: Execution context with attempts
            task: Task definition
            total_runtime: Total execution time
            
        Returns:
            ScoringResult with all metrics
        """
        # Get final attempt
        final_attempt = ctx.attempts[-1]
        
        # Get model output from last attempt
        model_output = final_attempt.model_output_raw
        
        return TaskScorer.score_execution(
            task_id=task.task_id,
            model_name=ctx.model_name,
            timestamp=datetime.utcnow().isoformat(),
            validation_report=final_attempt.validation_report,
            iterations_required=ctx.final_iteration,
            runtime_seconds=total_runtime,
            model_output=model_output,
            scoring_rules=task.scoring_rules,
            modified_template_path=ctx.workspace.template_file
        )


# Backward compatibility
def run_task(task_id: str, model_name: str) -> ExecutionContext:
    """Backward compatible task execution"""
    runner = TaskRunner()
    return runner.run_task(task_id, model_name)