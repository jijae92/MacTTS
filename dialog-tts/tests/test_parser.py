"""Tests for dialog parser."""

import pytest
from pathlib import Path
import tempfile
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser_utils import DialogParser, DialogLine, Directive


class TestDialogParser:
    """Test dialog script parser."""

    def test_parse_speaker_line(self):
        """Test parsing speaker lines."""
        parser = DialogParser()
        lines = [
            "A: Hello there",
            "B: How are you?",
        ]

        elements = parser.parse_lines(lines)

        assert len(elements) == 2
        assert isinstance(elements[0], DialogLine)
        assert elements[0].speaker == "A"
        assert elements[0].text == "Hello there"

        assert isinstance(elements[1], DialogLine)
        assert elements[1].speaker == "B"
        assert elements[1].text == "How are you?"

    def test_parse_fullwidth_colon(self):
        """Test parsing with full-width colon (：)."""
        parser = DialogParser()
        lines = [
            "A： 안녕하세요",
            "B: 반갑습니다",
        ]

        elements = parser.parse_lines(lines)

        assert len(elements) == 2
        assert elements[0].speaker == "A"
        assert elements[0].text == "안녕하세요"
        assert elements[1].speaker == "B"

    def test_parse_silence_directive(self):
        """Test parsing silence directive."""
        parser = DialogParser()
        lines = [
            "A: Hello",
            "[silence=400]",
            "B: Hi",
        ]

        elements = parser.parse_lines(lines)

        assert len(elements) == 3
        assert isinstance(elements[1], Directive)
        assert elements[1].type == "silence"
        assert elements[1].params['value'] == "400"

    def test_parse_sfx_directive(self):
        """Test parsing sound effect directive."""
        parser = DialogParser()
        lines = [
            "[sfx=samples/ring.wav vol=-6 pan=+0.2]",
        ]

        elements = parser.parse_lines(lines)

        assert len(elements) == 1
        assert isinstance(elements[0], Directive)
        assert elements[0].type == "sfx"
        assert elements[0].params['value'] == "samples/ring.wav"
        assert elements[0].params['vol'] == "-6"
        assert elements[0].params['pan'] == "+0.2"

    def test_parse_comments_and_blank_lines(self):
        """Test that comments and blank lines are ignored."""
        parser = DialogParser()
        lines = [
            "# This is a comment",
            "",
            "A: Hello",
            "  ",
            "# Another comment",
            "B: Hi",
        ]

        elements = parser.parse_lines(lines)

        assert len(elements) == 2
        assert all(isinstance(e, DialogLine) for e in elements)

    def test_speaker_aliases(self):
        """Test speaker alias resolution."""
        parser = DialogParser(speaker_aliases={
            "A": ["화자A", "Agent"],
            "B": ["화자B", "Customer"]
        })

        lines = [
            "화자A: 안녕하세요",
            "Agent: How are you?",
            "Customer: Fine, thanks",
            "화자B: 감사합니다",
        ]

        elements = parser.parse_lines(lines)

        assert len(elements) == 4
        # All should be normalized to canonical names
        assert elements[0].speaker == "A"
        assert elements[1].speaker == "A"
        assert elements[2].speaker == "B"
        assert elements[3].speaker == "B"

    def test_get_speakers(self):
        """Test extracting unique speakers."""
        parser = DialogParser()
        lines = [
            "A: Hello",
            "B: Hi",
            "A: How are you?",
            "[silence=400]",
            "C: Great!",
        ]

        elements = parser.parse_lines(lines)
        speakers = parser.get_speakers(elements)

        assert speakers == {"A", "B", "C"}

    def test_parse_file(self):
        """Test parsing from file."""
        parser = DialogParser()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("# Test dialog\n")
            f.write("A: Hello\n")
            f.write("B: Hi\n")
            f.write("[silence=500]\n")
            f.write("A: Goodbye\n")
            temp_path = Path(f.name)

        try:
            elements = parser.parse_file(temp_path)

            assert len(elements) == 4
            assert isinstance(elements[0], DialogLine)
            assert isinstance(elements[2], Directive)

        finally:
            temp_path.unlink()

    def test_parse_with_bom(self):
        """Test parsing file with BOM."""
        parser = DialogParser()

        # Create file with BOM
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8-sig') as f:
            f.write("A: Hello\n")
            temp_path = Path(f.name)

        try:
            elements = parser.parse_file(temp_path)
            assert len(elements) == 1
            assert elements[0].speaker == "A"

        finally:
            temp_path.unlink()


class TestSentenceSplitter:
    """Test sentence splitting."""

    def test_split_sentences(self):
        """Test basic sentence splitting."""
        from parser_utils import split_sentences

        text = "Hello. How are you? I'm fine!"
        sentences = split_sentences(text)

        assert len(sentences) == 3
        assert "Hello." in sentences[0]
        assert "How are you?" in sentences[1]
        assert "I'm fine!" in sentences[2]

    def test_split_korean_sentences(self):
        """Test splitting Korean sentences."""
        from parser_utils import split_sentences

        text = "안녕하세요. 어떻게 지내세요？ 저는 잘 지냅니다！"
        sentences = split_sentences(text)

        assert len(sentences) == 3

    def test_split_with_ellipsis(self):
        """Test splitting with ellipsis."""
        from parser_utils import split_sentences

        text = "Well… I don't know. Maybe?"
        sentences = split_sentences(text)

        # Ellipsis is treated as sentence ending, so this splits into 3 parts
        assert len(sentences) == 3
        assert "Well…" in sentences[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
