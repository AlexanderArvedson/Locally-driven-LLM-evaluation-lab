"""
Tests for patch engine module
"""

import pytest
from pathlib import Path
from evaluation_suite.patch_engine import PatchEngine
from evaluation_suite.output_parser import ParsedOutput, OutputFormat


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace with template"""
    ws = tmp_path / "workspace"
    ws.mkdir()
    
    template = ws / "template.py"
    template.write_text("def hello():\n    return 'old'\n")
    
    return ws


class TestPatchApplication:
    """Test patch application"""

    def test_apply_modification_success(self, temp_workspace):
        """Apply modification successfully"""
        # Make sure new content is different from original
        new_content = "def hello():\n    print('modified')\n    return 'new'\n    # Additional line\n"
        
        parsed = ParsedOutput(
            success=True,
            content=new_content,
            raw_output=new_content,
            format_detected=OutputFormat.RAW_CODE
        )
        
        result = PatchEngine.apply_modification(parsed, temp_workspace)
        
        assert result.success is True
        # Verify something changed
        assert result.original_hash != result.modified_hash

    def test_modification_written_to_disk(self, temp_workspace):
        """Modified file is written to disk"""
        new_content = "def hello():\n    return 'modified'\n"
        template_file = temp_workspace / "template.py"
        
        parsed = ParsedOutput(
            success=True,
            content=new_content,
            raw_output=new_content,
            format_detected=OutputFormat.RAW_CODE
        )
        
        PatchEngine.apply_modification(parsed, temp_workspace)
        
        # Verify file was modified
        updated = template_file.read_text()
        assert updated == new_content

    def test_hashing(self, temp_workspace):
        """File hashes are calculated"""
        new_content = "def hello():\n    return 'new'\n"
        
        parsed = ParsedOutput(
            success=True,
            content=new_content,
            raw_output=new_content,
            format_detected=OutputFormat.RAW_CODE
        )
        
        result = PatchEngine.apply_modification(parsed, temp_workspace)
        
        assert result.original_hash != ""
        assert result.modified_hash != ""
        assert result.original_hash != result.modified_hash

    def test_empty_content_fails(self, temp_workspace):
        """Empty content fails"""
        parsed = ParsedOutput(
            success=True,
            content="",
            raw_output="",
            format_detected=OutputFormat.RAW_CODE
        )
        
        result = PatchEngine.apply_modification(parsed, temp_workspace)
        
        assert result.success is False

    def test_nonexistent_file_fails(self, tmp_path):
        """Nonexistent target file fails"""
        workspace = tmp_path / "nonexistent"
        
        parsed = ParsedOutput(
            success=True,
            content="def test():\n    pass\n",
            raw_output="",
            format_detected=OutputFormat.RAW_CODE
        )
        
        result = PatchEngine.apply_modification(parsed, workspace)
        
        assert result.success is False

    def test_diff_summary(self, temp_workspace):
        """Generate diff summary"""
        original = temp_workspace / "original.py"
        original.write_text("def hello():\n    return 'original'\n")
        
        modified = temp_workspace / "modified.py"
        modified.write_text("def hello():\n    return 'modified'\n    # extra line\n")
        
        diff = PatchEngine.get_diff_summary(original, modified)
        
        assert diff is not None
        assert diff["lines_changed"] > 0
