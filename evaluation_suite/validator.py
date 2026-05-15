"""
Deterministic validation pipeline for task execution.

Validates modified files in strict order:
1. Syntax validation (ast.parse)
2. Import validation (importlib)
3. Test execution (pytest subprocess)
4. Regression detection (reference vs modified)
"""

import ast
import sys
import subprocess
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

from pydantic import BaseModel, Field
from loguru import logger


class ErrorType(str, Enum):
    """Categorized failure types from validation pipeline"""
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    VERIFICATION_FAILED = "verification_failed"
    TIMEOUT = "timeout"
    RUNTIME_CRASH = "runtime_crash"
    PATCH_APPLICATION_FAILED = "patch_application_failed"


class ValidationStage(str, Enum):
    """Validation pipeline stages"""
    SYNTAX = "syntax"
    IMPORTS = "imports"
    TESTS = "tests"
    REGRESSION = "regression"


class ValidationResult(BaseModel):
    """Result of a single validation stage"""
    passed: bool
    stage: ValidationStage
    error_type: Optional[ErrorType] = None
    error_message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    """Complete validation report for a task execution"""
    overall_passed: bool
    stages: List[ValidationResult] = Field(default_factory=list)
    regression_detected: bool = False
    regression_details: str = ""
    original_template_hash: str = ""
    modified_template_hash: str = ""


class TemplateValidator:
    """
    Validator for task template modifications.
    
    Executes deterministic validation in strict order:
    1. Syntax → 2. Imports → 3. Tests → 4. Regression
    
    Stops at first failure. Generates categorized error types.
    """

    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds

    def validate_syntax(self, filepath: Path) -> ValidationResult:
        """
        Validate Python syntax using ast.parse().
        
        Args:
            filepath: Path to Python file to validate
            
        Returns:
            ValidationResult with syntax_error or passed status
        """
        logger.info(f"Validating syntax: {filepath}")
        
        if not filepath.exists():
            return ValidationResult(
                passed=False,
                stage=ValidationStage.SYNTAX,
                error_type=ErrorType.PATCH_APPLICATION_FAILED,
                error_message=f"File not found: {filepath}",
                details={"filepath": str(filepath)}
            )
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            ast.parse(content)
            logger.info("✓ Syntax validation passed")
            
            return ValidationResult(
                passed=True,
                stage=ValidationStage.SYNTAX,
                details={"lines_of_code": len(content.splitlines())}
            )
            
        except IndentationError as e:
            logger.error(f"✗ Indentation error at line {e.lineno}")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.SYNTAX,
                error_type=ErrorType.SYNTAX_ERROR,
                error_message=f"Line {e.lineno}: Indentation error",
                details={
                    "line_number": e.lineno,
                    "message": str(e)
                }
            )

        except SyntaxError as e:
            logger.error(f"✗ Syntax error at line {e.lineno}: {e.msg}")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.SYNTAX,
                error_type=ErrorType.SYNTAX_ERROR,
                error_message=f"Line {e.lineno}: {e.msg}",
                details={
                    "line_number": e.lineno,
                    "offset": e.offset,
                    "text": e.text or "",
                    "message": e.msg
                }
            )
            
        except Exception as e:
            logger.error(f"✗ Unexpected syntax error: {str(e)}")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.SYNTAX,
                error_type=ErrorType.SYNTAX_ERROR,
                error_message=str(e),
                details={"exception_type": type(e).__name__}
            )

    def validate_imports(self, filepath: Path, workspace_root: Optional[Path] = None) -> ValidationResult:
        """
        Validate that imports can be resolved.
        
        Attempts to import the module and detects missing dependencies.
        
        Args:
            filepath: Path to Python file
            workspace_root: Root directory to add to sys.path for imports
            
        Returns:
            ValidationResult with import_error or passed status
        """
        logger.info(f"Validating imports: {filepath}")
        
        if workspace_root:
            if str(workspace_root) not in sys.path:
                sys.path.insert(0, str(workspace_root))
        
        module_name = filepath.stem
        
        try:
            # Try to compile the file
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            code = compile(content, filepath, "exec")
            
            # Try to execute in empty namespace to catch import errors
            namespace = {"__name__": "__main__", "__file__": str(filepath)}
            exec(code, namespace)
            
            logger.info("✓ Import validation passed")
            
            return ValidationResult(
                passed=True,
                stage=ValidationStage.IMPORTS,
                details={"module": module_name}
            )
            
        except ModuleNotFoundError as e:
            logger.error(f"✗ Missing module: {e.name}")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.IMPORTS,
                error_type=ErrorType.IMPORT_ERROR,
                error_message=f"Missing module: {e.name}",
                details={"missing_module": e.name}
            )
            
        except ImportError as e:
            logger.error(f"✗ Import error: {str(e)}")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.IMPORTS,
                error_type=ErrorType.IMPORT_ERROR,
                error_message=str(e),
                details={"import_error": str(e)}
            )
            
        except NameError as e:
            # NameError during execution might indicate undefined names
            logger.error(f"✗ Name error: {str(e)}")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.IMPORTS,
                error_type=ErrorType.IMPORT_ERROR,
                error_message=str(e),
                details={"name_error": str(e)}
            )
            
        except Exception as e:
            logger.error(f"✗ Unexpected import validation error: {str(e)}")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.IMPORTS,
                error_type=ErrorType.IMPORT_ERROR,
                error_message=str(e),
                details={"exception_type": type(e).__name__}
            )

    def validate_tests(
        self, 
        workspace_root: Path, 
        test_dir: Path,
        timeout_seconds: Optional[int] = None
    ) -> ValidationResult:
        """
        Execute pytest tests in isolated workspace.
        
        Args:
            workspace_root: Root directory of isolated workspace
            test_dir: Directory containing tests (relative or absolute)
            timeout_seconds: Timeout for pytest execution
            
        Returns:
            ValidationResult with verification_failed, timeout, runtime_crash, or passed
        """
        logger.info(f"Running tests in {workspace_root}")
        
        timeout = timeout_seconds or self.timeout_seconds
        
        if isinstance(test_dir, str):
            test_dir = Path(test_dir)
        
        # Make test_dir absolute if relative
        if not test_dir.is_absolute():
            test_dir = workspace_root / test_dir
        
        if not test_dir.exists():
            logger.error(f"✗ Test directory not found: {test_dir}")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.TESTS,
                error_type=ErrorType.VERIFICATION_FAILED,
                error_message=f"Test directory not found: {test_dir}",
                details={"test_dir": str(test_dir)}
            )
        
        try:
            # Run pytest with JSON output for detailed results
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    str(test_dir),
                    "-v",
                    "--tb=short",
                    "--no-header",
                    "-q"
                ],
                cwd=str(workspace_root),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Parse output
            stdout = result.stdout
            stderr = result.stderr
            
            if result.returncode == 0:
                logger.info("✓ All tests passed")
                return ValidationResult(
                    passed=True,
                    stage=ValidationStage.TESTS,
                    details={
                        "stdout": stdout,
                        "test_command": f"pytest {test_dir} -v"
                    }
                )
            else:
                logger.error(f"✗ Tests failed")
                return ValidationResult(
                    passed=False,
                    stage=ValidationStage.TESTS,
                    error_type=ErrorType.VERIFICATION_FAILED,
                    error_message="One or more pytest tests failed",
                    details={
                        "return_code": result.returncode,
                        "stdout": stdout,
                        "stderr": stderr,
                        "test_dir": str(test_dir)
                    }
                )
                
        except subprocess.TimeoutExpired:
            logger.error(f"✗ Tests timed out after {timeout}s")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.TESTS,
                error_type=ErrorType.TIMEOUT,
                error_message=f"Pytest execution timed out after {timeout} seconds",
                details={
                    "timeout_seconds": timeout,
                    "test_dir": str(test_dir)
                }
            )
            
        except FileNotFoundError:
            logger.error("✗ pytest not found or test execution failed")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.TESTS,
                error_type=ErrorType.RUNTIME_CRASH,
                error_message="Failed to execute pytest",
                details={"test_dir": str(test_dir)}
            )
            
        except Exception as e:
            logger.error(f"✗ Unexpected test execution error: {str(e)}")
            return ValidationResult(
                passed=False,
                stage=ValidationStage.TESTS,
                error_type=ErrorType.RUNTIME_CRASH,
                error_message=str(e),
                details={"exception_type": type(e).__name__}
            )

    def detect_regression(
        self,
        original_path: Path,
        modified_path: Path,
        reference_path: Path,
        workspace_root: Path,
        test_dir: Path
    ) -> tuple[bool, str]:
        """
        Detect regression: reference passes but modified fails on same tests.
        
        Args:
            original_path: Original template file
            modified_path: Modified template file
            reference_path: Reference solution file
            workspace_root: Workspace root for test execution
            test_dir: Directory containing tests
            
        Returns:
            Tuple of (regression_detected: bool, details: str)
        """
        logger.info("Checking for regressions")
        
        # Run tests against reference solution
        logger.info("Running tests against reference solution...")
        
        # Temporarily backup modified, use reference
        import shutil
        backup_path = modified_path.with_suffix(".backup")
        shutil.copy(modified_path, backup_path)
        
        try:
            shutil.copy(reference_path, modified_path)
            
            reference_result = self.validate_tests(workspace_root, test_dir)
            
            # Restore modified version
            shutil.copy(backup_path, modified_path)
            
            # Run tests against modified
            modified_result = self.validate_tests(workspace_root, test_dir)
            
            # Clean up backup
            backup_path.unlink()
            
            # Regression = reference passed but modified failed
            regression = reference_result.passed and not modified_result.passed
            
            details = ""
            if regression:
                logger.warning("⚠ Regression detected: reference passes but modified fails")
                details = (
                    f"Reference solution passes tests but modified solution fails. "
                    f"Modified error: {modified_result.error_message}"
                )
            else:
                logger.info("✓ No regression detected")
            
            return regression, details
            
        except Exception as e:
            logger.error(f"✗ Error during regression detection: {str(e)}")
            # Restore modified in case of error
            if backup_path.exists():
                shutil.copy(backup_path, modified_path)
                backup_path.unlink()
            return False, f"Regression detection error: {str(e)}"

    def run_full_validation(
        self,
        workspace_root: Path,
        template_file: str = "template.py",
        tests_dir: str = "tests",
        reference_file: str = "../reference.py"
    ) -> ValidationReport:
        """
        Execute full validation pipeline in strict order.
        
        Stops at first failure. Includes regression detection if all stages pass.
        
        Args:
            workspace_root: Root of isolated workspace
            template_file: Name of template file (relative to workspace_root)
            tests_dir: Name of tests directory (relative to workspace_root)
            reference_file: Path to reference solution (relative to workspace_root)
            
        Returns:
            ValidationReport with all stages and overall result
        """
        logger.info(f"Starting full validation pipeline for {workspace_root}")
        
        report = ValidationReport(overall_passed=False)
        
        template_path = workspace_root / template_file
        # Keep tests path relative here; validate_tests() resolves it against
        # workspace_root to support both relative and absolute inputs safely.
        tests_path = Path(tests_dir)
        reference_path = workspace_root / reference_file
        
        # Calculate hashes
        if template_path.exists():
            with open(template_path, "rb") as f:
                report.modified_template_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Stage 1: Syntax validation
        logger.info("═" * 50)
        logger.info("Stage 1/4: Syntax Validation")
        logger.info("═" * 50)
        
        syntax_result = self.validate_syntax(template_path)
        report.stages.append(syntax_result)
        
        if not syntax_result.passed:
            logger.error("Pipeline stopped: syntax validation failed")
            report.overall_passed = False
            return report
        
        # Stage 2: Import validation
        logger.info("\n" + "═" * 50)
        logger.info("Stage 2/4: Import Validation")
        logger.info("═" * 50)
        
        import_result = self.validate_imports(template_path, workspace_root)
        report.stages.append(import_result)
        
        if not import_result.passed:
            logger.error("Pipeline stopped: import validation failed")
            report.overall_passed = False
            return report
        
        # Stage 3: Test validation
        logger.info("\n" + "═" * 50)
        logger.info("Stage 3/4: Test Validation")
        logger.info("═" * 50)
        
        tests_result = self.validate_tests(workspace_root, tests_path)
        report.stages.append(tests_result)
        
        if not tests_result.passed:
            logger.error("Pipeline stopped: test validation failed")
            report.overall_passed = False
            return report
        
        # Stage 4: Regression detection (only if tests pass)
        logger.info("\n" + "═" * 50)
        logger.info("Stage 4/4: Regression Detection")
        logger.info("═" * 50)
        
        if reference_path.exists():
            regression_detected, regression_details = self.detect_regression(
                template_path,
                template_path,
                reference_path,
                workspace_root,
                tests_path
            )
            report.regression_detected = regression_detected
            report.regression_details = regression_details
        else:
            logger.warning(f"Reference solution not found at {reference_path}, skipping regression detection")
        
        logger.info("\n" + "═" * 50)
        logger.info("✓ Full validation pipeline passed")
        logger.info("═" * 50)
        
        report.overall_passed = True
        return report
