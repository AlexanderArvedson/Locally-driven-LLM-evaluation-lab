"""
Manage isolated per-run workspaces for task execution.

Each task run gets a fully isolated workspace under workspace/run_<uuid>/.
This ensures task templates are never modified directly and enables
per-run inspection and artifact preservation.
"""

import uuid
import shutil
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from loguru import logger


class IsolatedWorkspace(BaseModel):
    """Metadata for an isolated task execution workspace"""
    workspace_id: str = Field(description="UUID for this workspace")
    workspace_root: Path = Field(description="workspace/run_<uuid>/")
    task_dir: Path = Field(description="workspace/run_<uuid>/task/")
    template_file: Path = Field(description="workspace/run_<uuid>/task/template.py")
    tests_dir: Path = Field(description="workspace/run_<uuid>/task/tests/")
    reference_file: Path = Field(description="workspace/run_<uuid>/reference.py")
    spec_file: Path = Field(description="workspace/run_<uuid>/task/spec.json")

    class Config:
        arbitrary_types_allowed = True

    @property
    def relative_template(self) -> str:
        """Relative path to template from workspace root"""
        return "task/template.py"

    @property
    def relative_tests(self) -> str:
        """Relative path to tests from workspace root"""
        return "task/tests"

    @property
    def relative_reference(self) -> str:
        """Relative path to reference from workspace root"""
        return "reference.py"


class WorkspaceManager:
    """
    Create and manage isolated per-run workspaces.
    
    Structure:
    workspace/
      run_<uuid>/
        task/
          template.py        (file to be modified)
          tests/
            test_task.py
            __init__.py
          spec.json
        reference.py         (for regression detection)
    """

    def __init__(self, workspace_base: Optional[Path] = None):
        """
        Initialize workspace manager.
        
        Args:
            workspace_base: Base directory for workspaces (default: ./workspace)
        """
        self.workspace_base = workspace_base or Path("workspace")
        self.workspace_base.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace manager initialized at {self.workspace_base}")

    def create_workspace(self, task_template_dir: Path) -> IsolatedWorkspace:
        """
        Create isolated workspace for task execution.
        
        1. Create workspace/run_<uuid>/ directory
        2. Copy task template files
        3. Copy reference solution
        4. Copy test files
        5. Copy spec.json
        
        Args:
            task_template_dir: Path to task directory (e.g., tasks/task_01/)
            
        Returns:
            IsolatedWorkspace with all paths configured
        """
        workspace_id = str(uuid.uuid4())
        workspace_root = self.workspace_base / f"run_{workspace_id}"
        
        logger.info(f"Creating isolated workspace: {workspace_root}")
        
        # Create directory structure
        workspace_root.mkdir(parents=True, exist_ok=True)
        task_dir = workspace_root / "task"
        task_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Workspace directory structure created")
        
        # Copy template.py
        template_src = task_template_dir / "template.py"
        template_dst = task_dir / "template.py"
        
        if template_src.exists():
            shutil.copy2(template_src, template_dst)
            logger.info(f"✓ Copied template: {template_src} → {template_dst}")
        else:
            raise FileNotFoundError(f"Template not found: {template_src}")
        
        # Copy tests directory
        tests_src = task_template_dir / "tests"
        tests_dst = task_dir / "tests"
        
        if tests_src.exists():
            shutil.copytree(tests_src, tests_dst)
            logger.info(f"✓ Copied tests: {tests_src} → {tests_dst}")
        else:
            raise FileNotFoundError(f"Tests directory not found: {tests_src}")
        
        # Copy spec.json
        spec_src = task_template_dir / "spec.json"
        spec_dst = task_dir / "spec.json"
        
        if spec_src.exists():
            shutil.copy2(spec_src, spec_dst)
            logger.info(f"✓ Copied spec: {spec_src} → {spec_dst}")
        else:
            raise FileNotFoundError(f"Spec file not found: {spec_src}")
        
        # Copy reference.py to workspace root (for regression detection)
        reference_src = task_template_dir / "reference.py"
        reference_dst = workspace_root / "reference.py"
        
        if reference_src.exists():
            shutil.copy2(reference_src, reference_dst)
            logger.info(f"✓ Copied reference: {reference_src} → {reference_dst}")
        else:
            logger.warning(f"Reference solution not found: {reference_src}")
        
        # Create workspace metadata object
        workspace = IsolatedWorkspace(
            workspace_id=workspace_id,
            workspace_root=workspace_root,
            task_dir=task_dir,
            template_file=template_dst,
            tests_dir=tests_dst,
            reference_file=reference_dst,
            spec_file=spec_dst
        )
        
        logger.info(f"✓ Isolated workspace created: {workspace_id}")
        
        return workspace

    def cleanup_workspace(
        self,
        workspace_id: str,
        keep_artifacts: bool = True
    ) -> bool:
        """
        Clean up workspace after execution.
        
        Args:
            workspace_id: UUID of workspace to clean up
            keep_artifacts: If False, delete workspace entirely (default: True, keep for inspection)
            
        Returns:
            True if successful, False otherwise
        """
        workspace_root = self.workspace_base / f"run_{workspace_id}"
        
        if not workspace_root.exists():
            logger.warning(f"Workspace not found: {workspace_root}")
            return False
        
        if keep_artifacts:
            logger.info(f"Keeping workspace for inspection: {workspace_root}")
            return True
        else:
            try:
                shutil.rmtree(workspace_root)
                logger.info(f"✓ Cleaned up workspace: {workspace_root}")
                return True
            except Exception as e:
                logger.error(f"Failed to clean up workspace: {str(e)}")
                return False

    def get_workspace_path(self, workspace_id: str) -> Optional[Path]:
        """
        Get path to existing workspace.
        
        Args:
            workspace_id: UUID of workspace
            
        Returns:
            Path to workspace_root or None if not found
        """
        workspace_root = self.workspace_base / f"run_{workspace_id}"
        
        if workspace_root.exists():
            return workspace_root
        
        logger.warning(f"Workspace not found: {workspace_root}")
        return None

    def list_workspaces(self) -> list[str]:
        """
        List all existing workspaces.
        
        Returns:
            List of workspace UUIDs
        """
        workspaces = []
        
        try:
            for entry in self.workspace_base.iterdir():
                if entry.is_dir() and entry.name.startswith("run_"):
                    workspace_id = entry.name.replace("run_", "")
                    workspaces.append(workspace_id)
        except Exception as e:
            logger.error(f"Error listing workspaces: {str(e)}")
        
        return sorted(workspaces)
