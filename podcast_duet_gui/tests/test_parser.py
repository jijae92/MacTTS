"""
Tests for script parser.

Critical requirement: Directives must NEVER be synthesized as speech.
"""

import pytest
from pathlib import Path

from ..parser_rules import ScriptParser, TimelineEvent, parse_script


class TestScriptParser:
    """Test script parsing functionality."""

    def test_parse_simple_dialog(self):
        """Test parsing simple A:/B: dialog."""
        script = """
A: 안녕하세요.
B: 반갑습니다.
"""
        events = parse_script(script)

        assert len(events) == 2
        assert events[0].event_type == 'speech'
        assert events[0].speaker == 'A'
        assert events[0].text == '안녕하세요.'

        assert events[1].event_type == 'speech'
        assert events[1].speaker == 'B'
        assert events[1].text == '반갑습니다.'

    def test_parse_full_width_colon(self):
        """Test full-width colon support (：)."""
        script = "A： 안녕하세요."
        events = parse_script(script)

        assert len(events) == 1
        assert events[0].speaker == 'A'

    def test_silence_directive_not_speech(self):
        """
        CRITICAL: Directives must NOT be treated as speech.

        [silence=1s] must create a silence event, not speech.
        """
        script = """
A: Hello.
[silence=1s]
B: World.
"""
        events = parse_script(script)

        assert len(events) == 3
        assert events[0].event_type == 'speech'
        assert events[1].event_type == 'silence'  # NOT speech!
        assert events[1].duration_ms == 1000
        assert events[2].event_type == 'speech'

    def test_silence_milliseconds(self):
        """Test silence in milliseconds."""
        events = parse_script("[silence=500ms]")

        assert len(events) == 1
        assert events[0].event_type == 'silence'
        assert events[0].duration_ms == 500

    def test_silence_seconds(self):
        """Test silence in seconds."""
        events = parse_script("[silence=1.5s]")

        assert len(events) == 1
        assert events[0].duration_ms == 1500

    def test_sfx_directive(self):
        """Test SFX directive parsing."""
        script = "[sfx=sound.wav vol=-6 pan=0.3]"
        events = parse_script(script)

        assert len(events) == 1
        assert events[0].event_type == 'sfx'
        assert events[0].sfx_path == Path("sound.wav")
        assert events[0].sfx_volume_db == -6.0
        assert events[0].sfx_pan == 0.3

    def test_empty_lines_ignored(self):
        """Test that empty lines are skipped."""
        script = """
A: Hello.

B: World.
"""
        events = parse_script(script)

        assert len(events) == 2

    def test_comments_ignored(self):
        """Test that comment lines are skipped."""
        script = """
# This is a comment
A: Hello.
# Another comment
B: World.
"""
        events = parse_script(script)

        assert len(events) == 2

    def test_speaker_names(self):
        """Test different speaker name formats."""
        script = """
Alice: First speaker.
Bob-123: Second speaker.
전문가: Korean name.
"""
        events = parse_script(script)

        assert len(events) == 3
        assert events[0].speaker == 'Alice'
        assert events[1].speaker == 'Bob-123'
        assert events[2].speaker == '전문가'

    def test_get_speakers(self):
        """Test extracting unique speakers."""
        parser = ScriptParser()
        script = """
A: Hello.
B: Hi.
A: How are you?
C: Good.
"""
        parser.parse(script)
        speakers = parser.get_speakers()

        assert len(speakers) == 3
        assert 'A' in speakers
        assert 'B' in speakers
        assert 'C' in speakers

    def test_directive_never_becomes_speech(self):
        """
        CRITICAL TEST: Ensure directives are never mis-parsed as speech.

        This is the core requirement of the system.
        """
        script = """
A: Before directive.
[silence=1s]
[sfx=sound.wav]
B: After directive.
"""
        events = parse_script(script)

        # Check each event type
        speech_events = [e for e in events if e.event_type == 'speech']
        silence_events = [e for e in events if e.event_type == 'silence']
        sfx_events = [e for e in events if e.event_type == 'sfx']

        assert len(speech_events) == 2
        assert len(silence_events) == 1
        assert len(sfx_events) == 1

        # Verify directives are NOT in speech text
        for event in speech_events:
            assert '[silence' not in event.text
            assert '[sfx' not in event.text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
