"""
Load and validate task definitions from standardized task structure.

Each task has:
- template.py: File to be modified
- reference.py: Reference solution
- tests/test_task.py: Pytest validation tests
- spec.json: Task metadata and execution configuration
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict
from loguru import logger


class TaskMetadata(BaseModel):
    """Task metadata from spec.json"""
    task_id: str
    name: str
    category: str
    difficulty: str
    workflow: str
    language: str = "python"
    entry_file: str = "template.py"
    expected_behavior: str = ""
    
    model_config = ConfigDict(extra="allow")  # Allow additional fields


class ExecutionConfig(BaseModel):
    """Execution configuration for task"""
    max_iterations: int = 3
    timeout_seconds: int = 60
    validation_order: list[str] = Field(default_factory=lambda: ["syntax", "imports", "tests"])
    test_command: str = "pytest tests/ -v"
    
    model_config = ConfigDict(extra="allow")


class EvaluationConfig(BaseModel):
    """Evaluation and scoring configuration"""
    method: str = "rule_based_compliance"
    scoring_rules: Dict[str, Any] = Field(default_factory=dict)
    max_score: int = 10
    compliance_threshold: str = ""
    
    model_config = ConfigDict(extra="allow")


class TaskSpec(BaseModel):
    """Complete task specification from spec.json"""
    task_id: str
    name: str
    category: str
    difficulty: str
    workflow: str
    language: str = "python"
    entry_file: str = "template.py"
    expected_behavior: str = ""
    execution_config: ExecutionConfig = Field(default_factory=ExecutionConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    model_instructions: Dict[str, Any] = Field(default_factory=dict)
    expected_properties: Dict[str, Any] = Field(default_factory=dict)
    verification: Dict[str, Any] = Field(default_factory=dict)
    research_signal: str = ""
    notes: str = ""
    
    model_config = ConfigDict(extra="allow")


class Task(BaseModel):
    """Loaded and validated task with resource paths"""
    metadata: TaskMetadata
    spec: TaskSpec
    template_path: Path
    reference_path: Path
    tests_dir: Path
    spec_path: Path
    task_root: Path
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @property
    def task_id(self) -> str:
        """Task ID"""
        return self.metadata.task_id
    
    @property
    def max_iterations(self) -> int:
        """Maximum iterations for execution"""
        return self.spec.execution_config.max_iterations
    
    @property
    def timeout_seconds(self) -> int:
        """Timeout for task execution"""
        return self.spec.execution_config.timeout_seconds
    
    @property
    def scoring_rules(self) -> Dict[str, Any]:
        """Scoring rules for evaluation"""
        return self.spec.evaluation.scoring_rules


class TaskLoader:
    """
    Load and validate task definitions from standardized structure.
    
    Expected structure for each task:
    tasks/
      <task_id>/
        template.py          - File to be modified
        reference.py         - Reference solution
        tests/
          test_task.py       - Pytest tests
          __init__.py
        spec.json            - Task metadata
    """

    def __init__(self, tasks_base_dir: Optional[Path] = None):
        """
        Initialize task loader.
        
        Args:
            tasks_base_dir: Base directory containing tasks (default: evaluation_suite/tasks)
        """
        if tasks_base_dir is None:
            # Default to evaluation_suite/tasks relative to this module
            module_dir = Path(__file__).parent
            tasks_base_dir = module_dir / "tasks"
        
        self.tasks_base_dir = Path(tasks_base_dir)
        logger.info(f"Task loader initialized at {self.tasks_base_dir}")

    def load_task(self, task_id: str) -> Task:
        """
        Load task definition.
        
        Args:
            task_id: Task identifier (e.g., "task_01")
            
        Returns:
            Loaded Task with all resources validated
            
        Raises:
            FileNotFoundError: If task structure is incomplete
            ValueError: If task specification is invalid
        """
        task_root = self.tasks_base_dir / task_id
        
        logger.info(f"Loading task: {task_id}")
        
        # Verify task directory exists
        if not task_root.exists():
            raise FileNotFoundError(f"Task directory not found: {task_root}")
        
        # Verify required files
        template_path = task_root / "template.py"
        reference_path = task_root / "reference.py"
        tests_dir = task_root / "tests"
        spec_path = task_root / "spec.json"
        
        required_files = {
            "template.py": template_path,
            "reference.py": reference_path,
            "tests/": tests_dir,
            "spec.json": spec_path
        }
        
        for file_name, file_path in required_files.items():
            if not file_path.exists():
                raise FileNotFoundError(f"Required file not found: {file_name} at {file_path}")
        
        logger.info(f"✓ All required files present")
        
        # Load and parse spec.json
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec_data = json.load(f)
            logger.info(f"✓ Loaded spec.json")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in spec.json: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error reading spec.json: {str(e)}")
        
        # Validate task ID consistency
        if spec_data.get("task_id") != task_id:
            logger.warning(
                f"Task ID mismatch: directory '{task_id}' != spec.json '{spec_data.get('task_id')}'"
            )
        
        # Parse specifications
        try:
            task_spec = TaskSpec(**spec_data)
            metadata = TaskMetadata(**spec_data)
            logger.info(f"✓ Parsed task specification")
        except Exception as e:
            raise ValueError(f"Invalid task specification: {str(e)}")
        
        # Create Task object
        task = Task(
            metadata=metadata,
            spec=task_spec,
            template_path=template_path,
            reference_path=reference_path,
            tests_dir=tests_dir,
            spec_path=spec_path,
            task_root=task_root
        )
        
        logger.info(f"✓ Task loaded successfully: {task_id}")
        
        return task

    def list_available_tasks(self) -> list[str]:
        """
        List all available tasks.
        
        Returns:
            List of task IDs
        """
        task_ids = []
        
        try:
            for entry in self.tasks_base_dir.iterdir():
                if entry.is_dir() and (entry / "spec.json").exists():
                    task_ids.append(entry.name)
        except Exception as e:
            logger.error(f"Error listing tasks: {str(e)}")
        
        return sorted(task_ids)

    def validate_task_structure(self, task_id: str) -> bool:
        """
        Validate task directory structure without loading.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if structure is valid, False otherwise
        """
        task_root = self.tasks_base_dir / task_id
        
        if not task_root.is_dir():
            logger.error(f"Task directory not found: {task_root}")
            return False
        
        required_files = [
            "template.py",
            "reference.py",
            "tests",
            "spec.json"
        ]
        
        for file_name in required_files:
            file_path = task_root / file_name
            if not file_path.exists():
                logger.error(f"Missing: {task_id}/{file_name}")
                return False
        
        return True
