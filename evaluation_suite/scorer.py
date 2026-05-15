"""
Task execution scoring and metric calculation.

Computes all evaluation metrics:
- task_success: validation passed
- verification_passed: all tests passed
- regression_detected: reference passes but modified fails
- compliance_score: task-specific rule-based scoring (0-10)
- iterations_required: number of attempts
- lines_changed: diff calculation
- bytes_changed: diff calculation
- runtime_seconds: total execution time
- tokens_used: estimate from prompt/response
"""

import re
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field
from loguru import logger

from .validator import ValidationReport, ValidationStage
from .patch_engine import PatchResult


class ScoringResult(BaseModel):
    """Complete scoring metrics for task execution"""
    # Core outcomes
    task_success: bool = Field(description="Validation pipeline passed")
    verification_passed: bool = Field(description="All pytest tests passed")
    regression_detected: bool = Field(description="Reference passed but modified failed")
    
    # Compliance and scoring
    compliance_score: int = Field(ge=0, le=10, description="Task-specific compliance score (0-10)")
    
    # Execution metrics
    iterations_required: int = Field(ge=1, description="Number of attempts until success or max")
    lines_changed: int = Field(ge=0, description="Lines changed in modification")
    bytes_changed: int = Field(ge=0, description="Bytes changed in modification")
    runtime_seconds: float = Field(ge=0, description="Total execution time")
    tokens_used: int = Field(ge=0, description="Estimated tokens (prompt + response)")
    
    # Context
    model: str = Field(description="Model name (e.g., 'qwen2.5-coder')")
    task_id: str = Field(description="Task identifier")
    timestamp: str = Field(description="ISO 8601 timestamp")
    
    # Optional details
    model_output_length: int = Field(default=0, description="Length of raw model output")
    error_type: Optional[str] = Field(default=None, description="Error type if task_success=False")


class TaskScorer:
    """
    Score task execution based on validation results and execution metrics.
    
    Calculates:
    1. Task success from validation pipeline
    2. Compliance score from task-specific rules
    3. Regression detection from validation
    4. Metrics (iterations, lines changed, runtime, tokens)

    Note: Compliance checks intentionally use lightweight regex heuristics
    for speed and determinism. Test validation remains the source of truth.
    """

    @staticmethod
    def estimate_tokens(prompt: str, response: str) -> int:
        """
        Estimate token count from prompt and response.
        
        Rough estimate: ~1 token per 4 characters
        More accurate methods would use tokenizer, but this is a reasonable approximation.
        
        Args:
            prompt: Model input prompt
            response: Model response
            
        Returns:
            Estimated token count
        """
        # Simple heuristic: ~4 characters per token
        total_chars = len(prompt) + len(response)
        tokens = total_chars // 4
        return max(tokens, 0)

    @staticmethod
    def calculate_compliance_score(
        modified_template: Path,
        task_id: str,
        scoring_rules: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Calculate compliance score using task-specific rules.
        
        Implements pattern-matching based compliance checking:
        - Hard constraints (penalties): signature, no classes, no self
        - Soft checks (bonuses): deduplication, sorting, correct counts
        
        Args:
            modified_template: Path to modified template file
            task_id: Task identifier
            scoring_rules: Dict of scoring rules from task spec
            
        Returns:
            Compliance score (0-10)
        """
        logger.info("Calculating compliance score")
        
        if not modified_template.exists():
            logger.error(f"Modified template not found: {modified_template}")
            return 0
        
        try:
            with open(modified_template, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading template: {str(e)}")
            return 0
        
        score = 10  # Start with perfect score
        
        # If no rules provided, use default task-specific rules
        if not scoring_rules:
            scoring_rules = TaskScorer._get_default_rules(task_id)
        
        # Apply hard constraints (penalties)
        logger.info("Checking hard constraints (signature, no classes, no self)...")
        
        # Check 1: Function signature compliance
        signature_rule = scoring_rules.get("signature_compliance", {})
        check_for = signature_rule.get("check_for", "def generate_user_report(users)")
        penalty = signature_rule.get("penalty_if_violated", -3)
        
        if not TaskScorer._check_signature_compliance(content, check_for):
            logger.warning(f"✗ Signature violation")
            score += penalty
        else:
            logger.info(f"✓ Signature compliant")
        
        # Check 2: No class introduction
        no_class_rule = scoring_rules.get("no_class_introduction", {})
        penalty = no_class_rule.get("penalty_if_violated", -2)
        
        if TaskScorer._contains_class_definition(content):
            logger.warning(f"✗ Class definition introduced")
            score += penalty
        else:
            logger.info(f"✓ No class definitions")
        
        # Check 3: No self parameter (no method conversion)
        no_self_rule = scoring_rules.get("no_self_parameter", {})
        penalty = no_self_rule.get("penalty_if_violated", -3)
        
        if TaskScorer._contains_self_parameter(content):
            logger.warning(f"✗ Self parameter found (method conversion)")
            score += penalty
        else:
            logger.info(f"✓ No self parameter")
        
        # Apply soft checks (bonuses)
        logger.info("Checking soft features (deduplication, sorting, etc)...")
        
        # Check 4: Deduplication
        dedup_rule = scoring_rules.get("deduplication", {})
        points = dedup_rule.get("points", 2)
        if TaskScorer._checks_deduplication(content):
            logger.info(f"✓ Deduplication detected (+{points})")
            score += points
        
        # Check 5: Sorting
        sort_rule = scoring_rules.get("sorting_active_users", {})
        points = sort_rule.get("points", 2)
        if TaskScorer._checks_sorting(content):
            logger.info(f"✓ Sorting detected (+{points})")
            score += points
        
        # Check 6: Correct counts
        count_rule = scoring_rules.get("correct_counts", {})
        points = count_rule.get("points", 2)
        if TaskScorer._checks_correct_counts(content):
            logger.info(f"✓ Correct counts logic detected (+{points})")
            score += points
        
        # Check 7: Robust input handling
        input_rule = scoring_rules.get("robust_input_handling", {})
        points = input_rule.get("points", 1)
        if TaskScorer._checks_input_validation(content):
            logger.info(f"✓ Input validation detected (+{points})")
            score += points
        
        # Check 8: String return format
        return_rule = scoring_rules.get("string_return_format", {})
        points = return_rule.get("points", 1)
        if TaskScorer._checks_string_return(content):
            logger.info(f"✓ String return format (+{points})")
            score += points
        
        # Clamp to 0-10 range
        score = max(0, min(10, score))
        
        logger.info(f"Final compliance score: {score}/10")
        return score

    @staticmethod
    def _check_signature_compliance(content: str, expected_signature: str) -> bool:
        """Check if function has correct signature"""
        # Look for the function definition
        return bool(re.search(r'def\s+generate_user_report\s*\(\s*users\s*\)', content))

    @staticmethod
    def _contains_class_definition(content: str) -> bool:
        """Check if content contains class definitions"""
        # Look for class keyword (not in strings/comments)
        lines = content.split('\n')
        for line in lines:
            # Skip comments
            line = line.split('#')[0]
            if re.search(r'^\s*class\s+\w+', line):
                return True
        return False

    @staticmethod
    def _contains_self_parameter(content: str) -> bool:
        """Check if generate_user_report has self parameter"""
        return bool(re.search(r'def\s+generate_user_report\s*\(\s*self', content))

    @staticmethod
    def _checks_deduplication(content: str) -> bool:
        """Check for deduplication logic (set usage or seen tracking)"""
        return bool(re.search(r'set\s*\(', content)) or \
               bool(re.search(r'in\s+seen', content))

    @staticmethod
    def _checks_sorting(content: str) -> bool:
        """Check for sorting logic"""
        return bool(re.search(r'\.sort\s*\(', content)) or \
               bool(re.search(r'sorted\s*\(', content))

    @staticmethod
    def _checks_correct_counts(content: str) -> bool:
        """Check for active/inactive counting logic"""
        return bool(re.search(r'len\s*\(\s*active', content)) and \
               bool(re.search(r'len\s*\(\s*inactive', content))

    @staticmethod
    def _checks_input_validation(content: str) -> bool:
        """Check for input type validation"""
        return bool(re.search(r'isinstance\s*\(', content))

    @staticmethod
    def _checks_string_return(content: str) -> bool:
        """Check for string return format (.join() or concatenation)"""
        return bool(re.search(r'\.join\s*\(', content)) or \
               bool(re.search(r'return\s+f\'', content)) or \
               bool(re.search(r'return\s+f"', content))

    @staticmethod
    def _get_default_rules(task_id: str) -> Dict[str, Any]:
        """Get default scoring rules for known tasks"""
        # Default rules for task_01
        return {
            "signature_compliance": {
                "description": "Function signature must be: def generate_user_report(users)",
                "penalty_if_violated": -3,
                "check_for": "def generate_user_report(users)"
            },
            "no_class_introduction": {
                "description": "Must not introduce class definitions",
                "penalty_if_violated": -2,
                "check_for": "absence of 'class' keyword"
            },
            "no_self_parameter": {
                "description": "Must not convert to instance method with 'self'",
                "penalty_if_violated": -3,
                "check_for": "absence of 'def generate_user_report(self'"
            },
            "deduplication": {
                "points": 2,
                "check_for": "set() or 'seen' variable"
            },
            "sorting_active_users": {
                "points": 2,
                "check_for": "sort() or sorted() call"
            },
            "correct_counts": {
                "points": 2,
                "check_for": "active/inactive user counts"
            },
            "robust_input_handling": {
                "points": 1,
                "check_for": "isinstance() or type checks"
            },
            "string_return_format": {
                "points": 1,
                "check_for": "return statement with string concatenation or .join()"
            }
        }

    @staticmethod
    def score_execution(
        task_id: str,
        model_name: str,
        timestamp: str,
        validation_report: ValidationReport,
        patch_result: Optional[PatchResult] = None,
        iterations_required: int = 1,
        runtime_seconds: float = 0.0,
        model_output: str = "",
        scoring_rules: Optional[Dict[str, Any]] = None,
        modified_template_path: Optional[Path] = None
    ) -> ScoringResult:
        """
        Score complete task execution.
        
        Args:
            task_id: Task identifier
            model_name: Model name used
            timestamp: ISO 8601 timestamp
            validation_report: Full validation report
            patch_result: Patch application result (if available)
            iterations_required: Number of attempts
            runtime_seconds: Total runtime
            model_output: Raw model output for token estimation
            scoring_rules: Task-specific scoring rules
            modified_template_path: Path to modified template for compliance scoring
            
        Returns:
            Complete ScoringResult
        """
        logger.info(f"Scoring execution for {task_id} with {model_name}")
        
        # Determine success status
        task_success = validation_report.overall_passed
        
        # Check if tests passed
        tests_result = next(
            (stage for stage in validation_report.stages if stage.stage == ValidationStage.TESTS),
            None,
        )
        
        verification_passed = tests_result.passed if tests_result else False
        
        # Regression detection
        regression_detected = validation_report.regression_detected
        
        # Calculate compliance score
        compliance_score = 0
        if modified_template_path and modified_template_path.exists():
            compliance_score = TaskScorer.calculate_compliance_score(
                modified_template_path,
                task_id,
                scoring_rules
            )
        
        # Patch metrics
        lines_changed = patch_result.lines_changed if patch_result else 0
        bytes_changed = patch_result.bytes_changed if patch_result else 0
        
        # Estimate tokens
        tokens_used = TaskScorer.estimate_tokens(
            "",  # We don't have full prompt here
            model_output
        )
        
        # Determine error type if failed
        error_type = None
        if not task_success and validation_report.stages:
            error_type = validation_report.stages[-1].error_type.value if validation_report.stages[-1].error_type else None
        
        result = ScoringResult(
            task_success=task_success,
            verification_passed=verification_passed,
            regression_detected=regression_detected,
            compliance_score=compliance_score,
            iterations_required=iterations_required,
            lines_changed=lines_changed,
            bytes_changed=bytes_changed,
            runtime_seconds=runtime_seconds,
            tokens_used=tokens_used,
            model=model_name,
            task_id=task_id,
            timestamp=timestamp,
            model_output_length=len(model_output),
            error_type=error_type
        )
        
        logger.info(
            f"Scoring complete: "
            f"success={task_success}, "
            f"regression={regression_detected}, "
            f"compliance={compliance_score}, "
            f"iterations={iterations_required}"
        )
        
        return result


def score_model_output(output_text):
    score = 0
    max_score = 10
    compliance_issues = []

    if not output_text:
        return {
            "score": 0,
            "max_score": max_score,
            "normalized": 0,
            "compliance_issues": ["No output generated"]
        }

    # ===== COMPLIANCE CHECKS (HARD CONSTRAINTS) =====
    
    # 1. SIGNATURE COMPLIANCE: Function must be generate_user_report(users)
    has_correct_signature = "def generate_user_report(users)" in output_text
    has_self_parameter = "def generate_user_report(self" in output_text
    
    if has_self_parameter:
        score -= 3
        compliance_issues.append("CRITICAL: Function has 'self' parameter (introduced class method)")
    elif not has_correct_signature:
        score -= 2
        compliance_issues.append("WARNING: Function signature does not match required 'generate_user_report(users)'")
    else:
        score += 1  # Positive point for correct signature
    
    # 2. CLASS DETECTION: Function must be standalone, not a class method
    if "class " in output_text:
        score -= 2
        compliance_issues.append("CRITICAL: Code introduces unnecessary class definition (violates standalone requirement)")
    
    # 3. OOP DRIFT: Check for OOP patterns when not requested
    if "self." in output_text and "def generate_user_report(self" in output_text:
        score -= 2
        compliance_issues.append("CRITICAL: Function converted to instance method with 'self' references")
    
    # ===== FUNCTIONAL CHECKS (SOFT REQUIREMENTS) =====
    
    # 4. Deduplication logic (seen set)
    if "seen" in output_text or "set()" in output_text:
        score += 2
    else:
        compliance_issues.append("Missing deduplication logic")
    
    # 5. Sorting requirement
    if "sort" in output_text:
        score += 2
    else:
        compliance_issues.append("Missing sorting logic for active users")
    
    # 6. Active/inactive separation
    if "active" in output_text and "inactive" in output_text:
        score += 2
    else:
        compliance_issues.append("Missing active/inactive user separation")
    
    # 7. Input validation handling
    if "isinstance" in output_text or "None" in output_text or "type(" in output_text:
        score += 1
    
    # 8. String return format (should return string, not dict/object)
    if "return \"" in output_text or "return '" in output_text or ".join(" in output_text:
        score += 1
    else:
        compliance_issues.append("May not return string format (check return statements)")
    
    # Clamp score to max
    final_score = max(0, min(score, max_score))

    return {
        "score": final_score,
        "max_score": max_score,
        "normalized": final_score / max_score,
        "compliance_issues": compliance_issues,
        "is_compliant": has_correct_signature and not has_self_parameter and "class " not in output_text
    }