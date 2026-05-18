"""
Tests for task loader module
"""

import pytest
from pathlib import Path
from evaluation_suite.task_loader import TaskLoader, Task


@pytest.fixture
def task_loader():
    """Fixture providing TaskLoader instance"""
    return TaskLoader()


class TestTaskLoading:
    """Test task loading and validation"""

    def test_load_task_01(self, task_loader):
        """Load task_01 successfully"""
        task = task_loader.load_task("task_01")
        
        assert task.task_id == "task_01"
        assert task.metadata.name == "User report refactoring + bugfix"
        assert task.template_path.exists()
        assert task.reference_path.exists()
        assert task.tests_dir.exists()

    def test_task_properties(self, task_loader):
        """Verify task properties are accessible"""
        task = task_loader.load_task("task_01")
        
        assert task.max_iterations == 3
        assert task.timeout_seconds == 60
        assert task.scoring_rules is not None
        assert len(task.scoring_rules) > 0

    def test_task_files_exist(self, task_loader):
        """Verify all required task files exist"""
        task = task_loader.load_task("task_01")
        
        assert task.template_path.exists(), "template.py missing"
        assert task.reference_path.exists(), "reference.py missing"
        assert task.tests_dir.exists(), "tests/ directory missing"
        assert task.spec_path.exists(), "spec.json missing"

    def test_load_nonexistent_task(self, task_loader):
        """Loading nonexistent task raises error"""
        with pytest.raises(FileNotFoundError):
            task_loader.load_task("nonexistent_task")

    def test_list_available_tasks(self, task_loader):
        """List available tasks"""
        tasks = task_loader.list_available_tasks()
        
        assert len(tasks) > 0
        assert "task_01" in tasks

    def test_validate_task_structure(self, task_loader):
        """Validate task structure"""
        valid = task_loader.validate_task_structure("task_01")
        assert valid is True

    def test_validate_invalid_task_structure(self, task_loader):
        """Validate invalid task structure"""
        valid = task_loader.validate_task_structure("nonexistent")
        assert valid is False
