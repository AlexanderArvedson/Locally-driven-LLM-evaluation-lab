"""
Tests for workspace manager module
"""

import pytest
import shutil
from pathlib import Path
from evaluation_suite.workspace_manager import WorkspaceManager, IsolatedWorkspace
from evaluation_suite.task_loader import TaskLoader


@pytest.fixture
def workspace_manager(tmp_path):
    """Fixture providing WorkspaceManager with temp directory"""
    workspace_base = tmp_path / "workspaces"
    return WorkspaceManager(workspace_base)


@pytest.fixture
def task_01_dir():
    """Fixture providing path to task_01"""
    return Path(__file__).parent.parent / "evaluation_suite" / "tasks" / "task_01"


class TestWorkspaceCreation:
    """Test workspace creation and isolation"""

    def test_create_workspace(self, workspace_manager, task_01_dir):
        """Create workspace successfully"""
        workspace = workspace_manager.create_workspace(task_01_dir)
        
        assert workspace.workspace_root.exists()
        assert workspace.task_dir.exists()
        assert workspace.template_file.exists()
        assert workspace.tests_dir.exists()

    def test_workspace_isolation(self, workspace_manager, task_01_dir):
        """Workspace is properly isolated"""
        workspace = workspace_manager.create_workspace(task_01_dir)
        
        # Verify all required files are copied
        assert (workspace.workspace_root / "task" / "template.py").exists()
        assert (workspace.workspace_root / "task" / "tests" / "test_task.py").exists()
        assert (workspace.workspace_root / "reference.py").exists()

    def test_multiple_workspaces_independent(self, workspace_manager, task_01_dir):
        """Multiple workspaces are independent"""
        ws1 = workspace_manager.create_workspace(task_01_dir)
        ws2 = workspace_manager.create_workspace(task_01_dir)
        
        assert ws1.workspace_id != ws2.workspace_id
        assert ws1.workspace_root != ws2.workspace_root

    def test_get_workspace_path(self, workspace_manager, task_01_dir):
        """Get workspace path by ID"""
        ws = workspace_manager.create_workspace(task_01_dir)
        retrieved = workspace_manager.get_workspace_path(ws.workspace_id)
        
        assert retrieved == ws.workspace_root

    def test_list_workspaces(self, workspace_manager, task_01_dir):
        """List all workspaces"""
        ws1 = workspace_manager.create_workspace(task_01_dir)
        ws2 = workspace_manager.create_workspace(task_01_dir)
        
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) >= 2
        assert ws1.workspace_id in workspaces
        assert ws2.workspace_id in workspaces
