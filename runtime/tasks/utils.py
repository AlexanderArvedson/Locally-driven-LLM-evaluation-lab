"""Shared utilities for runtime tasks.

Small helpers extracted to avoid duplication between task implementations.
"""
import re
from typing import Dict


def extract_code_from_markdown(response: str, language: str) -> str:
    """Extract code fenced blocks from model responses.

    Tries language-specific fenced blocks first, then generic triple-backtick blocks.
    Falls back to returning the original response trimmed.
    """
    pattern = rf"```{re.escape(language)}\n(.*?)\n```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    pattern = r"```\n(.*?)\n```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    return response.strip()


def parse_simple_review(response: str) -> Dict[str, object]:
    """Parse a concise yes/no + score style review into structured data.

    This handles a few common patterns produced by the review prompts used
    in the runtime tasks.
    """
    review_data = {
        "approved": False,
        "feedback": response.strip(),
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
