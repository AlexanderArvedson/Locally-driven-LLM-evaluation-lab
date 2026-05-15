"""
Parse flexible model output formats and extract file modifications.

Supports both:
- Raw Python code (standalone or in markdown code blocks)
- JSON-wrapped format: {"file_path": "...", "content": "..."}

Automatically detects format and extracts content.
"""

import json
import re
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field
from loguru import logger


class OutputFormat(str, Enum):
    """Detected output format from model"""
    RAW_CODE = "raw_code"
    JSON_WRAPPED = "json_wrapped"
    MARKDOWN_WRAPPED = "markdown_wrapped"


class ParsedOutput(BaseModel):
    """Parsed model output with extracted content"""
    success: bool
    file_path: str = "template.py"
    content: str
    raw_output: str
    format_detected: OutputFormat
    extraction_error: Optional[str] = None


class OutputParser:
    """
    Parse flexible model output formats.
    
    Attempts format detection in order:
    1. JSON wrapper: {"file_path": "...", "content": "..."}
    2. Markdown code block: ```python ... ```
    3. Raw code: everything else
    
    Returns ParsedOutput with format info for debugging.
    """

    @staticmethod
    def _try_json_parse(text: str) -> Optional[ParsedOutput]:
        """
        Try to parse as JSON format: {"file_path": "...", "content": "..."}
        
        Returns ParsedOutput if successful, None otherwise.
        """
        try:
            # Try to find JSON object in text
            # First, try parsing entire text as JSON
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # Try finding JSON within the text (between { and })
                match = re.search(r'\{[^{}]*"file_path"[^{}]*"content"[^{}]*\}', text, re.DOTALL)
                if not match:
                    # Try reverse order (content before file_path)
                    match = re.search(r'\{[^{}]*"content"[^{}]*"file_path"[^{}]*\}', text, re.DOTALL)
                if not match:
                    return None
                data = json.loads(match.group(0))
            
            # Validate structure
            if not isinstance(data, dict):
                return None
            
            file_path = data.get("file_path", "template.py")
            content = data.get("content", "")
            
            if not isinstance(content, str) or not content.strip():
                return None
            
            logger.info(f"Detected JSON format: file_path={file_path}")
            
            return ParsedOutput(
                success=True,
                file_path=file_path,
                content=content,
                raw_output=text,
                format_detected=OutputFormat.JSON_WRAPPED
            )
            
        except Exception as e:
            logger.debug(f"JSON parsing failed: {str(e)}")
            return None

    @staticmethod
    def _try_markdown_parse(text: str) -> Optional[ParsedOutput]:
        """
        Try to extract Python code from markdown code block: ```python ... ```
        
        Returns ParsedOutput if successful, None otherwise.
        """
        try:
            # Look for markdown code block
            match = re.search(r'```(?:python)?\s*\n(.*?)\n```', text, re.DOTALL)
            
            if not match:
                return None
            
            content = match.group(1).strip()
            
            if not content:
                return None
            
            logger.info("Detected markdown code block format")
            
            return ParsedOutput(
                success=True,
                file_path="template.py",
                content=content,
                raw_output=text,
                format_detected=OutputFormat.MARKDOWN_WRAPPED
            )
            
        except Exception as e:
            logger.debug(f"Markdown parsing failed: {str(e)}")
            return None

    @staticmethod
    def _parse_raw_code(text: str) -> ParsedOutput:
        """
        Treat entire text as raw Python code.
        
        Always succeeds (fallback format).
        """
        content = text.strip()
        
        logger.info("Treating output as raw Python code")
        
        return ParsedOutput(
            success=True,
            file_path="template.py",
            content=content,
            raw_output=text,
            format_detected=OutputFormat.RAW_CODE
        )

    @staticmethod
    def parse(model_output: str, expected_file: str = "template.py") -> ParsedOutput:
        """
        Parse model output with automatic format detection.
        
        Tries formats in order:
        1. JSON wrapper
        2. Markdown code block
        3. Raw code (fallback)
        
        Args:
            model_output: Raw output from model
            expected_file: Expected file path (used if not in JSON)
            
        Returns:
            ParsedOutput with detected format and extracted content
        """
        if not model_output or not model_output.strip():
            logger.error("Empty model output")
            return ParsedOutput(
                success=False,
                file_path=expected_file,
                content="",
                raw_output=model_output,
                format_detected=OutputFormat.RAW_CODE,
                extraction_error="Empty output from model"
            )
        
        logger.info("Parsing model output...")
        
        # Try JSON format
        json_result = OutputParser._try_json_parse(model_output)
        if json_result:
            return json_result
        
        # Try markdown format
        markdown_result = OutputParser._try_markdown_parse(model_output)
        if markdown_result:
            return markdown_result
        
        # Fall back to raw code
        return OutputParser._parse_raw_code(model_output)
