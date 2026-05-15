"""
Shared pytest fixtures and configuration
"""

import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def evaluation_suite_dir(project_root):
    """Get evaluation_suite directory"""
    return project_root / "evaluation_suite"


@pytest.fixture(scope="session")
def tasks_dir(evaluation_suite_dir):
    """Get tasks directory"""
    return evaluation_suite_dir / "tasks"


@pytest.fixture(scope="session")
def task_01_dir(tasks_dir):
    """Get task_01 directory"""
    return tasks_dir / "task_01"


def pytest_configure(config):
    """Configure pytest"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
