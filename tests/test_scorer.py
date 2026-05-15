"""
Tests for scorer module
"""

import pytest
from pathlib import Path
from evaluation_suite.scorer import TaskScorer, ScoringResult
from evaluation_suite.validator import ValidationReport, ValidationStage


class TestTokenEstimation:
    """Test token estimation"""

    def test_estimate_tokens(self):
        """Estimate token count"""
        prompt = "This is a test prompt"
        response = "This is a test response"
        
        tokens = TaskScorer.estimate_tokens(prompt, response)
        
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_token_estimation_proportional(self):
        """Longer text estimates more tokens"""
        short = TaskScorer.estimate_tokens("short", "text")
        long = TaskScorer.estimate_tokens("this is a much longer prompt", "with a much longer response")
        
        assert long > short


class TestComplianceChecks:
    """Test compliance checking functions"""

    def test_signature_compliance_check(self):
        """Check function signature compliance"""
        valid = "def generate_user_report(users):"
        assert TaskScorer._check_signature_compliance(valid, valid) is True
        
        invalid = "def generate_user_report(users, context):"
        assert TaskScorer._check_signature_compliance(invalid, valid) is False

    def test_class_definition_detection(self):
        """Detect class definitions"""
        with_class = """
def generate_user_report(users):
    pass

class UserReport:
    pass
"""
        assert TaskScorer._contains_class_definition(with_class) is True
        
        without_class = "def generate_user_report(users):\n    pass\n"
        assert TaskScorer._contains_class_definition(without_class) is False

    def test_self_parameter_detection(self):
        """Detect self parameter"""
        with_self = "def generate_user_report(self, users):"
        assert TaskScorer._contains_self_parameter(with_self) is True
        
        without_self = "def generate_user_report(users):"
        assert TaskScorer._contains_self_parameter(without_self) is False

    def test_deduplication_check(self):
        """Detect deduplication logic"""
        with_set = "seen = set()"
        assert TaskScorer._checks_deduplication(with_set) is True
        
        with_list = "seen = []"
        assert TaskScorer._checks_deduplication(with_list) is False

    def test_sorting_check(self):
        """Detect sorting"""
        with_sort = "active.sort(key=lambda x: x['name'])"
        assert TaskScorer._checks_sorting(with_sort) is True
        
        without_sort = "active = []\ninactive = []"
        assert TaskScorer._checks_sorting(without_sort) is False

    def test_input_validation_check(self):
        """Detect input validation"""
        with_isinstance = "if isinstance(users, list):"
        assert TaskScorer._checks_input_validation(with_isinstance) is True
        
        without_validation = "return users"
        assert TaskScorer._checks_input_validation(without_validation) is False

    def test_string_return_check(self):
        """Detect string return format"""
        with_join = 'return "\\n".join(lines)'
        assert TaskScorer._checks_string_return(with_join) is True
        
        with_fstring = 'return f"Report: {data}"'
        assert TaskScorer._checks_string_return(with_fstring) is True
        
        without_string = 'return data'
        assert TaskScorer._checks_string_return(without_string) is False
