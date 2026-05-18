"""
Pytest validation tests for task_01: User report refactoring + bugfix
"""
import pytest
import sys
from pathlib import Path

# Import the reference solution for baseline validation
sys.path.insert(0, str(Path(__file__).parent.parent))
from reference import generate_user_report as reference_solution


# Test data fixtures
@pytest.fixture
def valid_users():
    """Valid user data with mix of active/inactive"""
    return [
        {"id": 1, "name": "Alice", "active": True},
        {"id": 2, "name": "Bob", "active": False},
        {"id": 3, "name": "Charlie", "active": True},
        {"id": 4, "name": "Diana", "active": False},
    ]


@pytest.fixture
def users_with_duplicates():
    """User data with duplicate IDs"""
    return [
        {"id": 1, "name": "Alice", "active": True},
        {"id": 2, "name": "Bob", "active": False},
        {"id": 1, "name": "Alice_Duplicate", "active": True},  # duplicate ID
        {"id": 3, "name": "Charlie", "active": True},
    ]


@pytest.fixture
def users_with_invalid_entries():
    """User data with invalid entries to be filtered"""
    return [
        {"id": 1, "name": "Alice", "active": True},
        {"id": 2},  # missing "name" and "active"
        "invalid_string",  # not a dict
        {"id": 3, "name": "Charlie"},  # missing "active"
        {"id": 4, "name": "Diana", "active": False},
    ]


@pytest.fixture
def users_unsorted():
    """User data that needs sorting"""
    return [
        {"id": 3, "name": "Charlie", "active": True},
        {"id": 1, "name": "Alice", "active": True},
        {"id": 2, "name": "Bob", "active": False},
        {"id": 4, "name": "Diana", "active": True},
    ]


# Basic functionality tests
class TestBasicFunctionality:
    """Tests for core functionality"""

    def test_returns_string(self, valid_users):
        """Output must be a string"""
        result = reference_solution(valid_users)
        assert isinstance(result, str), "Must return a string"

    def test_none_input_returns_string(self):
        """None input must return a string, not None"""
        result = reference_solution(None)
        assert isinstance(result, str), "Must return string for None input"
        assert result != "", "Should return meaningful message for None"

    def test_invalid_type_returns_string(self):
        """Invalid input type must return a string, not None"""
        result = reference_solution("not a list")
        assert isinstance(result, str), "Must return string for invalid type"

    def test_empty_list(self):
        """Empty list should return valid report"""
        result = reference_solution([])
        assert isinstance(result, str)
        assert "Total users: 0" in result


# Deduplication tests
class TestDeduplication:
    """Tests for duplicate removal by ID"""

    def test_removes_duplicates(self, users_with_duplicates):
        """Should remove duplicate user IDs"""
        result = reference_solution(users_with_duplicates)
        # Should have 3 unique users, not 4
        assert "Total users: 3" in result

    def test_keeps_first_occurrence(self, users_with_duplicates):
        """Should keep first occurrence of duplicate ID"""
        result = reference_solution(users_with_duplicates)
        # First Alice (id=1, active=True) should be kept
        assert "Alice" in result
        assert result.count("Alice") == 1  # only one Alice in report


# Active/Inactive separation tests
class TestActiveInactiveSeparation:
    """Tests for active/inactive user separation"""

    def test_separates_by_boolean_active(self, valid_users):
        """Should separate users by boolean active field"""
        result = reference_solution(valid_users)
        assert "ACTIVE USERS:" in result
        assert "INACTIVE USERS:" in result

    def test_correct_active_count(self, valid_users):
        """Should count active users correctly"""
        result = reference_solution(valid_users)
        # 2 active: Alice (True), Charlie (True)
        assert "Active users: 2" in result

    def test_correct_inactive_count(self, valid_users):
        """Should count inactive users correctly"""
        result = reference_solution(valid_users)
        # 2 inactive: Bob (False), Diana (False)
        assert "Inactive users: 2" in result

    def test_uses_boolean_comparison(self, valid_users):
        """Should use boolean comparison (is True), not string comparison"""
        result = reference_solution(valid_users)
        # With boolean check: 2 active
        assert "Active users: 2" in result
        # String comparison would give wrong results


# Sorting tests
class TestSorting:
    """Tests for active user sorting by name"""

    def test_active_users_sorted_alphabetically(self, users_unsorted):
        """Active users should be sorted by name"""
        result = reference_solution(users_unsorted)
        # Find position of active users in output
        active_section = result.split("ACTIVE USERS:")[1].split("INACTIVE")[0]
        lines = [line.strip() for line in active_section.strip().split("\n") if line.strip()]
        # Extract names and filter empty ones
        names = [line.split(" (")[0][2:] for line in lines if " (" in line]
        # Should have at least 3 active users
        assert len(names) >= 3
        assert names == sorted(names), f"Names {names} should be sorted"


# Input validation tests
class TestInputValidation:
    """Tests for robust input handling"""

    def test_filters_invalid_entries(self, users_with_invalid_entries):
        """Should filter out invalid entries"""
        result = reference_solution(users_with_invalid_entries)
        # Only 2 valid entries: Alice (complete), Diana (complete)
        assert "Total users: 2" in result

    def test_skips_non_dict_items(self):
        """Should skip non-dict items"""
        users = [
            {"id": 1, "name": "Alice", "active": True},
            "not a dict",
            123,
            None,
            {"id": 2, "name": "Bob", "active": False},
        ]
        result = reference_solution(users)
        assert "Total users: 2" in result

    def test_missing_required_fields_skipped(self):
        """Should skip entries missing required fields"""
        users = [
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob"},  # missing "active"
            {"id": 3, "active": False},  # missing "name"
            {"id": 4, "name": "Diana", "active": False},
        ]
        result = reference_solution(users)
        assert "Total users: 2" in result


# Output format tests
class TestOutputFormat:
    """Tests for output format and determinism"""

    def test_contains_required_sections(self, valid_users):
        """Output should contain all required sections"""
        result = reference_solution(valid_users)
        assert "USER REPORT" in result
        assert "==========" in result
        assert "Total users:" in result
        assert "Active users:" in result
        assert "Inactive users:" in result
        assert "ACTIVE USERS:" in result
        assert "INACTIVE USERS:" in result

    def test_uses_newline_not_escaped_newline(self, valid_users):
        """Should use actual newlines, not escaped \\n"""
        result = reference_solution(valid_users)
        assert "\n" in result
        assert "\\n" not in result

    def test_deterministic_output(self, valid_users):
        """Output should be deterministic"""
        result1 = reference_solution(valid_users)
        result2 = reference_solution(valid_users)
        assert result1 == result2, "Same input should produce identical output"

    def test_consistent_formatting(self, valid_users):
        """User entries should have consistent format"""
        result = reference_solution(valid_users)
        # Check that user lines follow pattern: "- Name (id: X)"
        lines = result.split("\n")
        user_lines = [l for l in lines if l.startswith("- ")]
        for line in user_lines:
            assert " (id: " in line, f"User line should have format '- Name (id: X)': {line}"


# Signature compliance tests
class TestSignatureCompliance:
    """Tests for function signature compliance"""

    def test_function_signature_unchanged(self):
        """Function must have signature: def generate_user_report(users)"""
        import inspect
        sig = inspect.signature(reference_solution)
        params = list(sig.parameters.keys())
        assert params == ["users"], f"Signature should have only 'users' parameter, got {params}"

    def test_no_self_parameter(self):
        """Function must not have 'self' parameter"""
        import inspect
        sig = inspect.signature(reference_solution)
        params = list(sig.parameters.keys())
        assert "self" not in params, "Function must not be a method with 'self' parameter"


# Edge cases
class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_single_user(self):
        """Single user should work"""
        users = [{"id": 1, "name": "Alice", "active": True}]
        result = reference_solution(users)
        assert "Total users: 1" in result

    def test_all_active(self):
        """All active users"""
        users = [
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob", "active": True},
        ]
        result = reference_solution(users)
        assert "Active users: 2" in result
        assert "Inactive users: 0" in result

    def test_all_inactive(self):
        """All inactive users"""
        users = [
            {"id": 1, "name": "Alice", "active": False},
            {"id": 2, "name": "Bob", "active": False},
        ]
        result = reference_solution(users)
        assert "Active users: 0" in result
        assert "Inactive users: 2" in result

    def test_special_characters_in_names(self):
        """Names with special characters should be handled"""
        users = [
            {"id": 1, "name": "Alice O'Brien", "active": True},
            {"id": 2, "name": "Bob & Co.", "active": False},
            {"id": 3, "name": "Charlie 中文", "active": True},
        ]
        result = reference_solution(users)
        assert "Alice O'Brien" in result
        assert "Bob & Co." in result
        assert "Total users: 3" in result
