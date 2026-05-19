from __future__ import annotations

import ast
from typing import Any, Dict, Optional

from ..prompts import generate_refactoring_prompt, generate_review_prompt
from .base import RuntimeTask


class RefactoringTask(RuntimeTask):
    """Task implementation for code refactoring workflows."""

    task_type = "refactoring"

    def normalize_context(self, optional_context: Optional[str]) -> str:
        return optional_context if optional_context else ""

    def build_generation_prompt(self, code: str, language: str, context: str) -> str:
        return generate_refactoring_prompt(code=code, language=language, context=context)

    def build_review_prompt(
        self,
        original_code: str,
        generated_code: str,
        language: str,
        context: str,
    ) -> str:
        return generate_review_prompt(
            original_code=original_code,
            generated_code=generated_code,
            language=language,
            context=context,
        )

    def extract_generated_code(self, response: str, language: str) -> str:
        import re

        pattern = rf"```{re.escape(language)}\n(.*?)\n```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1)

        pattern = r"```\n(.*?)\n```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1)

        return response.strip()

    def verify_generated_code(self, generated_code: str, language: str) -> Dict[str, Any]:
        verification: Dict[str, Any] = {
            "passed": False,
            "stage": "syntax",
            "details": {},
            "error_message": "",
        }

        if not generated_code or not generated_code.strip():
            verification["error_message"] = "No generated code to verify"
            return verification

        if language.lower() != "python":
            verification["passed"] = True
            verification["details"] = {"skipped": True, "reason": f"syntax verification not implemented for {language}"}
            return verification

        try:
            ast.parse(generated_code)
            verification["passed"] = True
            verification["details"] = {"syntax": "passed"}
            return verification
        except SyntaxError as exc:
            verification["error_message"] = f"Line {exc.lineno}: {exc.msg}"
            verification["details"] = {
                "line_number": exc.lineno,
                "offset": exc.offset,
                "text": exc.text or "",
            }
            return verification
        except Exception as exc:
            verification["error_message"] = str(exc)
            verification["details"] = {"exception_type": type(exc).__name__}
            return verification

    def parse_review_response(self, response: str) -> Dict[str, Any]:
        import re

        review_data: Dict[str, Any] = {
            "approved": False,
            "feedback": response,
            "score": 0.0,
        }

        if re.search(r"\byes\b", response, re.IGNORECASE):
            review_data["approved"] = True
        elif re.search(r"\bno\b", response, re.IGNORECASE):
            review_data["approved"] = False

        score_match = re.search(r"(\d+)\s*(?:/10|out of 10)", response, re.IGNORECASE)
        if score_match:
            try:
                score = int(score_match.group(1))
                review_data["score"] = min(10, max(0, score))
            except ValueError:
                pass

        return review_data