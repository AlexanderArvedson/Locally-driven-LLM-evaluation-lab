"""
Apply parsed model output to isolated workspace via full file replacement.

Strategy: Complete file replacement (not diff-based patching)
- Simpler and more stable
- Easier debugging and inspection
- Fewer parsing failure modes
- Diff-based patching can be added later
"""

import hashlib
import difflib
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from loguru import logger

from .output_parser import ParsedOutput


class PatchResult(BaseModel):
    """Result of applying modifications to workspace"""
    success: bool
    file_modified: str = ""
    error: Optional[str] = None
    bytes_changed: int = 0
    lines_changed: int = 0
    original_hash: str = ""
    modified_hash: str = ""


class PatchEngine:
    """
    Apply parsed model output to isolated workspace.
    
    Uses full file replacement strategy:
    - Overwrite target file with parsed_output.content
    - Calculate diff metrics (lines, bytes changed)
    - Track file hashes before/after for reproducibility
    - Handle encoding errors gracefully
    """

    @staticmethod
    def apply_modification(
        parsed_output: ParsedOutput,
        workspace_root: Path,
        target_file: str = "template.py"
    ) -> PatchResult:
        """
        Apply parsed model output to target file in workspace.
        
        Implements full file replacement strategy:
        1. Verify target file exists
        2. Calculate original hash
        3. Write new content
        4. Calculate diff metrics
        5. Return detailed PatchResult
        
        Args:
            parsed_output: Parsed model output with content
            workspace_root: Root of isolated workspace
            target_file: Target file to modify (relative to workspace_root)
            
        Returns:
            PatchResult with success status and metrics
        """
        logger.info(f"Applying modification to {workspace_root}/{target_file}")
        
        target_path = workspace_root / target_file
        
        # Verify target exists
        if not target_path.exists():
            logger.error(f"Target file not found: {target_path}")
            return PatchResult(
                success=False,
                file_modified=str(target_path),
                error=f"Target file not found: {target_path}"
            )
        
        # Read original content
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                original_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read original file: {str(e)}")
            return PatchResult(
                success=False,
                file_modified=str(target_path),
                error=f"Failed to read file: {str(e)}"
            )
        
        # Calculate original hash
        original_hash = hashlib.sha256(original_content.encode("utf-8")).hexdigest()
        
        # Verify we have content to write
        if not parsed_output.content:
            logger.error("No content to write from parsed output")
            return PatchResult(
                success=False,
                file_modified=str(target_path),
                error="Parsed output content is empty",
                original_hash=original_hash
            )
        
        # Write modified content
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(parsed_output.content)
            logger.info(f"✓ Modified file written: {target_path}")
        except Exception as e:
            logger.error(f"Failed to write modified file: {str(e)}")
            return PatchResult(
                success=False,
                file_modified=str(target_path),
                error=f"Failed to write file: {str(e)}",
                original_hash=original_hash
            )
        
        # Calculate modified hash
        modified_hash = hashlib.sha256(parsed_output.content.encode("utf-8")).hexdigest()
        
        # Calculate diff metrics
        lines_changed = PatchEngine._calculate_lines_changed(
            original_content,
            parsed_output.content
        )
        bytes_changed = abs(len(parsed_output.content) - len(original_content))
        
        logger.info(
            f"Patch applied: {lines_changed} lines changed, {bytes_changed} bytes changed"
        )
        
        return PatchResult(
            success=True,
            file_modified=str(target_path),
            bytes_changed=bytes_changed,
            lines_changed=lines_changed,
            original_hash=original_hash,
            modified_hash=modified_hash
        )

    @staticmethod
    def _calculate_lines_changed(original: str, modified: str) -> int:
        """
        Calculate approximate number of lines changed using difflib.
        
        Args:
            original: Original content
            modified: Modified content
            
        Returns:
            Number of lines changed
        """
        try:
            original_lines = original.splitlines(keepends=False)
            modified_lines = modified.splitlines(keepends=False)
            
            # Use SequenceMatcher to find differences
            matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
            
            # Count changed/deleted/inserted lines
            changes = 0
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag != 'equal':
                    changes += max(i2 - i1, j2 - j1)
            
            return changes
        except Exception as e:
            logger.warning(f"Error calculating line diff: {str(e)}")
            # Fallback: simple line count difference
            return abs(len(original.splitlines()) - len(modified.splitlines()))

    @staticmethod
    def get_diff_summary(original_path: Path, modified_path: Path) -> Optional[dict]:
        """
        Generate diff summary between original and modified files.
        
        Args:
            original_path: Path to original file
            modified_path: Path to modified file
            
        Returns:
            Dictionary with diff summary or None if files not found
        """
        try:
            with open(original_path, "r", encoding="utf-8") as f:
                original = f.read()
            with open(modified_path, "r", encoding="utf-8") as f:
                modified = f.read()
            
            original_lines = original.splitlines()
            modified_lines = modified.splitlines()
            
            # Create unified diff
            diff = list(difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile=str(original_path),
                tofile=str(modified_path),
                lineterm=""
            ))
            
            # Count additions/deletions
            additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
            deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
            
            return {
                "lines_added": additions,
                "lines_deleted": deletions,
                "lines_changed": additions + deletions,
                "diff_lines": len(diff),
                "original_line_count": len(original_lines),
                "modified_line_count": len(modified_lines)
            }
        except Exception as e:
            logger.error(f"Error generating diff summary: {str(e)}")
            return None
