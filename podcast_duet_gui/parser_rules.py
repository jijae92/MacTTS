"""
Dialog script parser for podcast synthesis.

Parses A:/B: speaker labels and directives like [silence=1s].
Directives are NEVER synthesized as speech - only processed as audio effects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class TimelineEvent:
    """Single event in the podcast timeline."""
    line_number: int
    event_type: str  # 'speech', 'silence', 'sfx'
    speaker: Optional[str] = None
    text: Optional[str] = None
    duration_ms: Optional[int] = None
    sfx_path: Optional[Path] = None
    sfx_volume_db: float = 0.0
    sfx_pan: float = 0.0

    def __repr__(self) -> str:
        if self.event_type == 'speech':
            return f"Speech(L{self.line_number}, {self.speaker}: {self.text[:30]}...)"
        elif self.event_type == 'silence':
            return f"Silence(L{self.line_number}, {self.duration_ms}ms)"
        elif self.event_type == 'sfx':
            return f"SFX(L{self.line_number}, {self.sfx_path.name})"
        return f"Event(L{self.line_number})"


class ScriptParser:
    """Parse podcast scripts with speaker labels and directives."""

    # Speaker label: "A: text" or "Speaker Name： text" (full-width colon supported)
    SPEAKER_PATTERN = re.compile(
        r'^(?P<speaker>[\w\-\s가-힣]+)\s*[:：]\s*(?P<text>.*)$'
    )

    # Directive: [key=value]
    DIRECTIVE_PATTERN = re.compile(
        r'^\[(?P<key>\w+)\s*=\s*(?P<value>[^\]]+)\]$'
    )

    def __init__(self):
        self.events: List[TimelineEvent] = []
        self.speakers_found: set[str] = set()

    def parse(self, script_text: str) -> List[TimelineEvent]:
        """
        Parse script text into timeline events.

        Args:
            script_text: Multi-line script with A:/B: labels and [directives]

        Returns:
            List of TimelineEvent objects
        """
        self.events = []
        self.speakers_found = set()

        lines = script_text.split('\n')

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Try to parse as directive
            directive_match = self.DIRECTIVE_PATTERN.match(line)
            if directive_match:
                event = self._parse_directive(
                    line_num,
                    directive_match.group('key'),
                    directive_match.group('value')
                )
                if event:
                    self.events.append(event)
                continue

            # Try to parse as speaker line
            speaker_match = self.SPEAKER_PATTERN.match(line)
            if speaker_match:
                speaker = speaker_match.group('speaker').strip()
                text = speaker_match.group('text').strip()

                if text:  # Only add if there's actual text
                    self.speakers_found.add(speaker)
                    event = TimelineEvent(
                        line_number=line_num,
                        event_type='speech',
                        speaker=speaker,
                        text=text
                    )
                    self.events.append(event)
                continue

            # Unrecognized format - log warning but continue
            print(f"Warning: Line {line_num} unrecognized format: {line[:50]}")

        return self.events

    def _parse_directive(
        self,
        line_num: int,
        key: str,
        value: str
    ) -> Optional[TimelineEvent]:
        """Parse a directive like [silence=1s] or [sfx=path vol=-6 pan=0.3]."""

        if key == 'silence':
            duration_ms = self._parse_duration(value)
            return TimelineEvent(
                line_number=line_num,
                event_type='silence',
                duration_ms=duration_ms
            )

        elif key == 'sfx':
            # Parse: path [vol=-6] [pan=0.3]
            return self._parse_sfx_directive(line_num, value)

        else:
            print(f"Warning: Unknown directive '{key}' at line {line_num}")
            return None

    def _parse_duration(self, value: str) -> int:
        """
        Parse duration string to milliseconds.

        Supports:
        - 1000ms, 1000
        - 1s, 1.5s
        """
        value = value.strip().lower()

        # Milliseconds: "1000ms" or just "1000"
        if value.endswith('ms'):
            return int(value[:-2])

        # Seconds: "1s" or "1.5s"
        if value.endswith('s'):
            return int(float(value[:-1]) * 1000)

        # Default to milliseconds
        try:
            return int(value)
        except ValueError:
            print(f"Warning: Invalid duration '{value}', defaulting to 500ms")
            return 500

    def _parse_sfx_directive(self, line_num: int, value: str) -> TimelineEvent:
        """Parse [sfx=path vol=-6 pan=0.3] directive."""
        parts = value.split()

        if not parts:
            print(f"Warning: Empty sfx directive at line {line_num}")
            return None

        sfx_path = Path(parts[0])
        volume_db = 0.0
        pan = 0.0

        # Parse optional vol= and pan= parameters
        for part in parts[1:]:
            if '=' in part:
                param, val = part.split('=', 1)
                param = param.strip().lower()

                if param == 'vol':
                    try:
                        volume_db = float(val)
                    except ValueError:
                        print(f"Warning: Invalid volume '{val}' at line {line_num}")

                elif param == 'pan':
                    try:
                        pan = max(-1.0, min(1.0, float(val)))
                    except ValueError:
                        print(f"Warning: Invalid pan '{val}' at line {line_num}")

        return TimelineEvent(
            line_number=line_num,
            event_type='sfx',
            sfx_path=sfx_path,
            sfx_volume_db=volume_db,
            sfx_pan=pan
        )

    def get_speakers(self) -> set[str]:
        """Return all unique speakers found in the script."""
        return self.speakers_found.copy()


def parse_script(script_text: str) -> List[TimelineEvent]:
    """
    Convenience function to parse a script.

    Example:
        >>> script = '''
        ... A: 안녕하세요.
        ... B: 반갑습니다.
        ... [silence=1s]
        ... A: 오늘은 좋은 날이에요.
        ... '''
        >>> events = parse_script(script)
        >>> len(events)
        4
    """
    parser = ScriptParser()
    return parser.parse(script_text)
