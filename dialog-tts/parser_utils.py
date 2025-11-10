"""Script parser for dialog TTS with speaker labels and directives."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Union


@dataclass
class DialogLine:
    """Represents a single line of dialog."""
    speaker: str
    text: str
    line_number: int


@dataclass
class Directive:
    """Represents a directive like [silence=400] or [sfx=path.wav vol=-6]."""
    type: str
    params: Dict[str, str]
    line_number: int


DialogElement = Union[DialogLine, Directive]


class DialogParser:
    """Parses dialog scripts with speaker labels and directives."""

    # Regex patterns
    # Matches: "Speaker: text" or "Speaker： text" (full-width colon)
    SPEAKER_PATTERN = re.compile(r'^(?P<speaker>[\w\-\s가-힣]+)\s*[:：]\s*(?P<line>.*)$')

    # Matches: "[key=value param2=value2]"
    DIRECTIVE_PATTERN = re.compile(r'^\[(?P<content>.+?)\]$')

    # Comment/blank line patterns
    COMMENT_PATTERN = re.compile(r'^\s*#')
    BLANK_PATTERN = re.compile(r'^\s*$')

    def __init__(self, speaker_aliases: Optional[Dict[str, List[str]]] = None):
        """
        Initialize parser.

        Args:
            speaker_aliases: Maps canonical speaker names to lists of aliases
                           e.g., {"A": ["화자A", "Agent", "상담원"]}
        """
        self.speaker_aliases = speaker_aliases or {}
        # Build reverse lookup: alias -> canonical name
        self._alias_lookup: Dict[str, str] = {}
        for canonical, aliases in self.speaker_aliases.items():
            for alias in aliases:
                self._alias_lookup[alias.strip()] = canonical

    def parse_file(self, file_path: Path) -> List[DialogElement]:
        """Parse a dialog script file."""
        with open(file_path, 'r', encoding='utf-8-sig') as f:  # Handle BOM
            lines = f.readlines()

        return self.parse_lines(lines)

    def parse_lines(self, lines: List[str]) -> List[DialogElement]:
        """Parse dialog script lines."""
        elements: List[DialogElement] = []

        for i, raw_line in enumerate(lines, start=1):
            # Normalize line: strip trailing whitespace, handle CRLF
            line = raw_line.rstrip('\r\n').rstrip()

            # Skip comments and blank lines
            if self.COMMENT_PATTERN.match(line) or self.BLANK_PATTERN.match(line):
                continue

            # Try to parse as directive
            directive = self._parse_directive(line, i)
            if directive:
                elements.append(directive)
                continue

            # Try to parse as speaker line
            speaker_line = self._parse_speaker_line(line, i)
            if speaker_line:
                elements.append(speaker_line)
                continue

            # If neither, log warning but continue
            print(f"Warning: Could not parse line {i}: {line[:50]}")

        return elements

    def _parse_speaker_line(self, line: str, line_number: int) -> Optional[DialogLine]:
        """Parse a speaker line like 'A: Hello there'."""
        match = self.SPEAKER_PATTERN.match(line)
        if not match:
            return None

        speaker = match.group('speaker').strip()
        text = match.group('line').strip()

        # Skip if no actual text
        if not text:
            return None

        # Resolve aliases
        canonical_speaker = self._alias_lookup.get(speaker, speaker)

        return DialogLine(
            speaker=canonical_speaker,
            text=text,
            line_number=line_number
        )

    def _parse_directive(self, line: str, line_number: int) -> Optional[Directive]:
        """Parse a directive like [silence=400] or [sfx=path.wav vol=-6 pan=+0.3]."""
        match = self.DIRECTIVE_PATTERN.match(line)
        if not match:
            return None

        content = match.group('content').strip()

        # Parse key=value pairs
        # First token is type (e.g., "silence=400" -> type is "silence")
        parts = content.split()
        if not parts:
            return None

        # Parse first part as type=value
        first_part = parts[0]
        if '=' not in first_part:
            return None

        directive_type, first_value = first_part.split('=', 1)
        params = {'value': first_value.strip()}

        # Parse additional parameters
        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                params[key.strip()] = value.strip()

        return Directive(
            type=directive_type.strip(),
            params=params,
            line_number=line_number
        )

    def get_speakers(self, elements: List[DialogElement]) -> set[str]:
        """Extract unique speaker names from parsed elements."""
        speakers = set()
        for element in elements:
            if isinstance(element, DialogLine):
                speakers.add(element.speaker)
        return speakers


def split_sentences(text: str) -> List[str]:
    """
    Split text into sentences at punctuation boundaries.

    Splits on: . ? ! ？ ！ …
    """
    # Pattern to split on sentence-ending punctuation
    # Keep the punctuation with the sentence
    pattern = r'([.?!？！…]+)'
    parts = re.split(pattern, text)

    sentences = []
    current = ""

    for part in parts:
        if not part.strip():
            continue

        current += part

        # If this part ends with punctuation, complete the sentence
        if re.match(pattern, part):
            sentences.append(current.strip())
            current = ""

    # Add any remaining text
    if current.strip():
        sentences.append(current.strip())

    return sentences if sentences else [text]


def normalize_text(text: str) -> str:
    """Normalize text for TTS processing."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
