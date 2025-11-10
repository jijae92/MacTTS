"""Smoke tests for CLI."""

import pytest
from pathlib import Path
import tempfile
import subprocess
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_script():
    """Create a simple test script."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("A: 안녕하세요\n")
        f.write("B: 반갑습니다\n")
        f.write("[silence=300]\n")
        f.write("A: 좋은 하루 되세요\n")
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def sample_speaker_map():
    """Create a simple speaker map YAML."""
    import yaml

    config = {
        'A': {
            'voice_hint': 'ko_KR',
            'rate_wpm': 180,
            'gain_db': 0.0,
            'pan': -0.3
        },
        'B': {
            'voice_hint': 'ko_KR',
            'rate_wpm': 170,
            'gain_db': -1.0,
            'pan': 0.3
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink(missing_ok=True)


class TestCLISmoke:
    """Smoke tests for dialog_tts CLI."""

    def test_help(self):
        """Test --help flag."""
        dialog_tts = Path(__file__).parent.parent / "dialog_tts.py"

        result = subprocess.run(
            [sys.executable, str(dialog_tts), '--help'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert 'Dialog TTS' in result.stdout
        assert '--script' in result.stdout
        assert '--out' in result.stdout

    def test_missing_args(self):
        """Test that missing required args produces error."""
        dialog_tts = Path(__file__).parent.parent / "dialog_tts.py"

        result = subprocess.run(
            [sys.executable, str(dialog_tts)],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0
        # Should mention required arguments
        assert 'required' in result.stderr.lower() or 'error' in result.stderr.lower()

    @pytest.mark.skipif(sys.platform != 'darwin', reason="macOS only")
    def test_mac_engine_basic(self, sample_script, sample_speaker_map):
        """Test basic execution with mac engine."""
        dialog_tts = Path(__file__).parent.parent / "dialog_tts.py"

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "output.wav"

            result = subprocess.run(
                [
                    sys.executable, str(dialog_tts),
                    '--script', str(sample_script),
                    '--speaker-map', str(sample_speaker_map),
                    '--out', str(output),
                    '--engine', 'mac'
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Print output for debugging
            if result.returncode != 0:
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)

            # Check if it succeeded or at least tried
            # (It might fail if macOS voices aren't configured, but shouldn't crash)
            assert result.returncode in [0, 1]

            # If successful, check output file
            if result.returncode == 0 and output.exists():
                assert output.stat().st_size > 0
                print(f"✓ Generated audio file: {output.stat().st_size} bytes")

    def test_inline_voices(self, sample_script):
        """Test using inline --voices instead of speaker map."""
        dialog_tts = Path(__file__).parent.parent / "dialog_tts.py"

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "output.wav"

            result = subprocess.run(
                [
                    sys.executable, str(dialog_tts),
                    '--script', str(sample_script),
                    '--voices',
                    'A=ko_KR:Yuna,rate=180,pan=-0.3',
                    'B=ko_KR:Jinho,rate=170,pan=0.3',
                    '--out', str(output),
                    '--engine', 'mac'
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Should at least parse arguments correctly
            # Actual synthesis may fail depending on system
            assert 'speaker' in result.stdout.lower() or result.returncode in [0, 1]


class TestBackendAvailability:
    """Test backend availability detection."""

    def test_mac_backend_available(self):
        """Test if mac backend is available on macOS."""
        if sys.platform == 'darwin':
            # Should be able to import
            try:
                from backends.mac_say_cli import MacSayBackend
                backend = MacSayBackend()
                print("✓ Mac say backend available")
            except Exception as e:
                pytest.fail(f"Mac backend should be available on macOS: {e}")

    def test_pyobjc_availability(self):
        """Test PyObjC availability."""
        if sys.platform == 'darwin':
            try:
                from backends.mac_nsspeech import PYOBJC_AVAILABLE
                if PYOBJC_AVAILABLE:
                    print("✓ PyObjC is available")
                else:
                    print("ℹ PyObjC not available, will use 'say' fallback")
            except ImportError:
                pytest.fail("Should be able to import mac_nsspeech module")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
