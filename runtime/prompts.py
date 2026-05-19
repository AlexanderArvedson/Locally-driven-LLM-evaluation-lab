"""
Prompt templates for code refactoring workflow.
"""

from typing import Optional


def generate_refactoring_prompt(
    code: str,
    language: str,
    context: Optional[str] = None,
) -> str:
    """
    Generate a prompt for code refactoring.

    Args:
        code: The code to refactor.
        language: Programming language of the code.
        context: Optional context or requirements for refactoring.

    Returns:
        A formatted prompt for the LLM.
    """
    prompt = f"""Refactor the following {language} code for clarity, efficiency, and best practices.

Code to refactor:
```{language}
{code}
```"""
    
    if context:
        prompt += f"\n\nAdditional context or requirements:\n{context}"
    
    prompt += "\n\nProvide the refactored code in a code block."
    
    return prompt


def generate_review_prompt(
    original_code: str,
    generated_code: str,
    language: str,
    context: Optional[str] = None,
) -> str:
    """
    Generate a prompt for reviewing refactored code.

    Args:
        original_code: The original code.
        generated_code: The refactored code to review.
        language: Programming language of the code.
        context: Optional context or requirements.

    Returns:
        A formatted prompt for the LLM.
    """
    prompt = f"""Review the refactored {language} code below. 

Original code:
```{language}
{original_code}
```

Refactored code:
```{language}
{generated_code}
```"""
    
    if context:
        prompt += f"\n\nContext/Requirements:\n{context}"
    
    prompt += """

Provide your review in the following format:
1. Is the refactored code an improvement? (yes/no)
2. What are the main improvements?
3. Any issues or concerns?
4. Overall score (1-10)

Be concise and specific."""
    
    return prompt


def generate_documentation_prompt(
    code: str,
    language: str,
    context: Optional[str] = None,
) -> str:
    """Generate a prompt for documentation-focused code updates."""
    prompt = f"""Improve the documentation for the following {language} code.

Add or improve docstrings and inline comments where they clarify intent.
Preserve the code's behavior and return the fully documented code in a code block.

Code to document:
```{language}
{code}
```"""

    if context:
        prompt += f"\n\nDocumentation requirements:\n{context}"

    prompt += "\n\nReturn only the documented code in a code block."

    return prompt


def generate_documentation_review_prompt(
    original_code: str,
    generated_code: str,
    language: str,
    context: Optional[str] = None,
) -> str:
    """Generate a prompt for reviewing documentation-focused updates."""
    prompt = f"""Review the documented {language} code below.

Original code:
```{language}
{original_code}
```

Documented code:
```{language}
{generated_code}
```"""

    if context:
        prompt += f"\n\nDocumentation requirements:\n{context}"

    prompt += """

Provide your review in the following format:
1. Does the code have clearer documentation? (yes/no)
2. What documentation improvements were made?
3. Any issues or concerns?
4. Overall score (1-10)

Be concise and specific."""

    return prompt
