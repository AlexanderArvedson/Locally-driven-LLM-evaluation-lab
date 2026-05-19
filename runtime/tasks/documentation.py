from __future__ import annotations

import ast
from typing import Any, Dict, Optional

from ..prompts import generate_documentation_prompt, generate_documentation_review_prompt
from .base import RuntimeTask


class DocumentationTask(RuntimeTask):
    """Task implementation for documentation-focused maintenance."""

    task_type = "documentation"

    def normalize_context(self, optional_context: Optional[str]) -> str:
        return optional_context if optional_context else ""

    def build_generation_prompt(self, code: str, language: str, context: str) -> str:
        return generate_documentation_prompt(code=code, language=language, context=context)

    def build_review_prompt(
        self,
        original_code: str,
        generated_code: str,
        language: str,
        context: str,
    ) -> str:
        return generate_documentation_review_prompt(
            original_code=original_code,
            generated_code=generated_code,
            language=language,
            context=context,
        )

    def extract_generated_code(self, response: str, language: str) -> str:
        from .utils import extract_code_from_markdown

        return extract_code_from_markdown(response, language)

    def verify_generated_code(self, generated_code: str, language: str) -> Dict[str, Any]:
        verification: Dict[str, Any] = {
            "passed": False,
            "stage": "documentation",
            "details": {},
            "error_message": "",
        }

        if not generated_code or not generated_code.strip():
            verification["error_message"] = "No documented output generated"
            return verification

        if language.lower() == "python":
            try:
                ast.parse(generated_code)
            except SyntaxError as exc:
                verification["error_message"] = f"Line {exc.lineno}: {exc.msg}"
                verification["details"] = {
                    "line_number": exc.lineno,
                    "offset": exc.offset,
                    "text": exc.text or "",
                }
                return verification

            has_docstrings_or_comments = (
                '"""' in generated_code
                or "'''" in generated_code
                or "#" in generated_code
            )

            if not has_docstrings_or_comments:
                verification["error_message"] = "No docstrings or comments detected"
                verification["details"] = {"syntax": "passed", "documentation": "missing"}
                return verification

            verification["passed"] = True
            verification["details"] = {"syntax": "passed", "documentation": "present"}
            return verification

        verification["passed"] = True
        verification["details"] = {
            "skipped": True,
            "reason": f"documentation verification not implemented for {language}",
        }
        return verification

    def parse_review_response(self, response: str) -> Dict[str, Any]:
        from .utils import parse_simple_review

        return parse_simple_review(response)