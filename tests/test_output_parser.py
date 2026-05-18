"""
Tests for output parser module
"""

import pytest
from evaluation_suite.output_parser import OutputParser, OutputFormat


class TestRawCodeParsing:
    """Test raw code parsing"""

    def test_parse_raw_code(self):
        """Parse raw Python code"""
        code = """def hello():
    return "world"
"""
        result = OutputParser.parse(code)
        
        assert result.success is True
        assert result.content == code.strip()
        assert result.format_detected == OutputFormat.RAW_CODE

    def test_parse_markdown_code_block(self):
        """Parse code in markdown code block"""
        output = """Here's the fixed code:

```python
def hello():
    return "world"
```

That's it!"""
        
        result = OutputParser.parse(output)
        
        assert result.success is True
        assert "def hello():" in result.content
        assert result.format_detected == OutputFormat.MARKDOWN_WRAPPED

    def test_parse_json_format(self):
        """Parse JSON-wrapped format"""
        output = """{
    "file_path": "template.py",
    "content": "def hello():\\n    return \\"world\\""
}"""
        
        result = OutputParser.parse(output)
        
        assert result.success is True
        assert result.file_path == "template.py"
        assert result.format_detected == OutputFormat.JSON_WRAPPED

    def test_parse_empty_output(self):
        """Handle empty output"""
        result = OutputParser.parse("")
        
        assert result.success is False
        assert result.extraction_error is not None

    def test_parse_detects_format_correctly(self):
        """Format detection prioritizes JSON over markdown"""
        # JSON should be detected first
        output = '{"file_path": "test.py", "content": "```python\\ndef test():\\n    pass\\n```"}'
        
        result = OutputParser.parse(output)
        
        assert result.format_detected == OutputFormat.JSON_WRAPPED

    def test_parse_markdown_fallback(self):
        """Fallback to markdown if JSON fails"""
        output = """```
def test():
    pass
```"""
        
        result = OutputParser.parse(output)
        
        assert result.format_detected == OutputFormat.MARKDOWN_WRAPPED
