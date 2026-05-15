"""
Persist task execution results and artifacts.

Result structure:
results/
  singular_runs/
    run_<uuid>/
      result.json           (ExecutionResult serialized)
      artifacts/
        modified_template.py
        validation_report.json
"""

import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field
from loguru import logger

from .scorer import ScoringResult
from .validator import ValidationReport
from .workspace_manager import IsolatedWorkspace
from .task_loader import Task


class RunArtifacts(BaseModel):
    """Artifacts preserved from a run"""
    run_id: str
    original_template_hash: str = ""
    modified_template_path: str = ""
    reference_solution_hash: str = ""
    test_suite_hash: str = ""
    validation_report_path: str = ""


class ExecutionAttempt(BaseModel):
    """Single execution attempt in a run"""
    iteration: int
    timestamp: str
    model_output_raw: str
    duration_seconds: float
    validation_report: ValidationReport
    success: bool


class ExecutionResult(BaseModel):
    """Complete result of task execution"""
    run_id: str
    timestamp: str
    task_id: str
    task_name: str
    model_name: str
    execution_attempts: list[ExecutionAttempt] = Field(default_factory=list)
    scoring: ScoringResult
    artifacts: RunArtifacts
    runtime_logs: str = ""
    notes: Optional[str] = None


class ResultStore:
    """
    Persist and manage execution results.
    
    Structure:
    results/
      singular_runs/
        run_<uuid>/
          result.json
          artifacts/
            modified_template.py
            validation_report.json
    """

    def __init__(self, results_base: Optional[Path] = None):
        """
        Initialize result store.
        
        Args:
            results_base: Base directory for results (default: results/singular_runs)
        """
        if results_base is None:
            results_base = Path("results") / "singular_runs"
        
        self.results_base = Path(results_base)
        self.results_base.mkdir(parents=True, exist_ok=True)
        logger.info(f"Result store initialized at {self.results_base}")

    def save_result(
        self,
        run_id: str,
        execution_result: ExecutionResult,
        workspace: Optional[IsolatedWorkspace] = None,
        task: Optional[Task] = None
    ) -> str:
        """
        Save execution result and artifacts.
        
        1. Create results/singular_runs/run_<uuid>/ directory
        2. Copy modified template to artifacts/
        3. Save validation report to artifacts/
        4. Save result.json with full ExecutionResult
        
        Args:
            run_id: Unique run identifier (UUID)
            execution_result: ExecutionResult with scoring and attempts
            workspace: IsolatedWorkspace with modified files
            task: Task definition for metadata
            
        Returns:
            Path to saved result.json
        """
        result_dir = self.results_base / f"run_{run_id}"
        result_dir.mkdir(parents=True, exist_ok=True)
        
        artifacts_dir = result_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving result to {result_dir}")
        
        # Copy artifacts if workspace provided
        if workspace and workspace.template_file.exists():
            try:
                template_dst = artifacts_dir / "modified_template.py"
                shutil.copy2(workspace.template_file, template_dst)
                execution_result.artifacts.modified_template_path = "artifacts/modified_template.py"
                logger.info(f"✓ Copied modified template")
            except Exception as e:
                logger.warning(f"Failed to copy modified template: {str(e)}")
            
            # Save validation report
            try:
                report_dst = artifacts_dir / "validation_report.json"
                with open(report_dst, "w", encoding="utf-8") as f:
                    json.dump(execution_result.execution_attempts[-1].validation_report.dict(), f, indent=2)
                execution_result.artifacts.validation_report_path = "artifacts/validation_report.json"
                logger.info(f"✓ Saved validation report")
            except Exception as e:
                logger.warning(f"Failed to save validation report: {str(e)}")
        
        # Save result.json
        result_path = result_dir / "result.json"
        
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(execution_result.dict(), f, indent=2, default=str)
            logger.info(f"✓ Saved result.json")
        except Exception as e:
            logger.error(f"Failed to save result: {str(e)}")
            raise
        
        logger.info(f"✓ Result persisted: {result_path}")
        
        return str(result_path)

    def load_result(self, run_id: str) -> Optional[ExecutionResult]:
        """
        Load execution result from disk.
        
        Args:
            run_id: Run identifier
            
        Returns:
            ExecutionResult or None if not found
        """
        result_path = self.results_base / f"run_{run_id}" / "result.json"
        
        if not result_path.exists():
            logger.warning(f"Result not found: {result_path}")
            return None
        
        try:
            with open(result_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            logger.info(f"Loaded result: {run_id}")
            return ExecutionResult(**data)
        except Exception as e:
            logger.error(f"Error loading result: {str(e)}")
            return None

    def list_results(self, limit: Optional[int] = None) -> list[str]:
        """
        List all saved results.
        
        Args:
            limit: Maximum number of results to return (most recent first)
            
        Returns:
            List of run IDs
        """
        results = []
        
        try:
            for entry in sorted(self.results_base.iterdir(), reverse=True):
                if entry.is_dir() and entry.name.startswith("run_"):
                    run_id = entry.name.replace("run_", "")
                    results.append(run_id)
                    
                    if limit and len(results) >= limit:
                        break
        except Exception as e:
            logger.error(f"Error listing results: {str(e)}")
        
        return results

    @staticmethod
    def calculate_file_hash(filepath: Path) -> str:
        """
        Calculate SHA256 hash of file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Hex digest of SHA256 hash
        """
        try:
            sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating hash for {filepath}: {str(e)}")
            return ""
