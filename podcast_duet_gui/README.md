# 🎙️ Podcast Duet - Two-Speaker TTS GUI

Professional podcast synthesis application with timeline-based dialog editing.

## Features

- **📝 Script Editor**: Write A:/B: dialog scripts with syntax highlighting
- **📋 Timeline View**: Visual representation of speech, silence, and SFX events
- **🎤 Speaker Configuration**: Assign different voices to each speaker
- **🎵 Audio Processing**: Professional podcast audio with panning, normalization
- **⚡ MacTTS Integration**: Uses LocalKoreanTTS engine with automatic fallback

## Script Format

```
A: 안녕하세요, 오늘은 좋은 날이에요.
B: 네, 맞아요. 날씨가 정말 좋네요.
[silence=1s]
A: 그래서 저는 산책을 하려고 합니다.
B: 좋은 생각이에요!
```

### Supported Directives

**Directives are NEVER synthesized as speech - only processed as audio effects.**

- `[silence=1s]` or `[silence=1000ms]` - Insert silence
- `[sfx=path vol=-6 pan=0.3]` - Insert sound effect with volume and panning

### Speaker Labels

- `A: text` - Standard format
- `Speaker Name: text` - Named speakers
- `전문가： text` - Full-width colon supported (：)

## Installation

### Prerequisites

```bash
# macOS
brew install ffmpeg

# Windows
# Download ffmpeg from ffmpeg.org

# Install Python dependencies
pip install -r requirements.txt
```

### Dependencies

- **PySide6**: Qt GUI framework
- **pydub**: Audio processing (requires ffmpeg)
- **pyloudnorm**: LUFS normalization (optional)
- **LocalKoreanTTS**: TTS engine (from parent project)

## Usage

### Run the GUI

```bash
# From podcast_duet_gui directory
python -m podcast_duet_gui.app

# Or from parent MacTTS directory
python -m podcast_duet_gui.app
```

### Workflow

1. **Load Voices**: Click "🔄 Load Voices from MacTTS"
2. **Write Script**: Enter dialog in A:/B: format
3. **Parse**: Click "⚙️ Parse" to analyze script
4. **Configure Speakers**: Assign voices to speakers A and B
5. **Synthesize**: Click "🎵 Synthesize Podcast"

## Architecture

```
podcast_duet_gui/
├── app.py              # Main GUI application
├── parser_rules.py     # A:/B: script parser
├── engine_bridge.py    # MacTTS integration layer
├── audio_pipeline.py   # pydub audio processing
├── timeline_model.py   # Qt table model for timeline
└── tests/
    └── test_parser.py  # Parser tests
```

## API Usage

### Parse Script Programmatically

```python
from podcast_duet_gui import parse_script

script = """
A: 안녕하세요.
B: 반갑습니다.
[silence=1s]
A: 좋은 하루 되세요!
"""

events = parse_script(script)

for event in events:
    print(f"{event.event_type}: {event.speaker} - {event.text}")
```

### Engine Bridge

```python
from podcast_duet_gui import get_bridge

bridge = get_bridge()
voices = bridge.get_voices()

for voice in voices:
    print(voice)  # Voice(name='SunHi', engine='edge')
```

## Testing

```bash
# Run tests
pytest podcast_duet_gui/tests/

# Run specific test
pytest podcast_duet_gui/tests/test_parser.py -v
```

## Critical Requirements

1. **Directives Must Not Be Synthesized**
   - `[silence=1s]` creates a silence event, NOT speech
   - `[sfx=...]` loads audio file, NOT text-to-speech
   - This is tested in `test_directive_never_becomes_speech`

2. **Speaker Label Parsing**
   - Both `:` and `：` (full-width) supported
   - Speaker names can contain Korean characters

3. **Audio Quality**
   - Stereo panning for speaker separation
   - LUFS normalization for consistent loudness
   - Crossfade at sentence boundaries (optional)

## Troubleshooting

### ffmpeg Not Found

```
Error: ffmpeg is not installed or not in PATH
```

**Solution:**
- macOS: `brew install ffmpeg`
- Windows: Download from https://ffmpeg.org
- Linux: `sudo apt install ffmpeg`

### MacTTS Import Failed

```
⚠️  MacTTS import failed, will use CLI
```

This is normal. The app will fall back to calling `localkoreantts` CLI.

### Voice List Empty

Click "🔄 Load Voices from MacTTS" to populate voice list.

## Future Enhancements

- [ ] Background synthesis with progress tracking
- [ ] LUFS normalization support
- [ ] Sentence-level crossfade
- [ ] Waveform visualization
- [ ] Project save/load (.podcast.json)
- [ ] PyInstaller builds for macOS/Windows

## License

Same as parent MacTTS project (MIT).

## Contributing

This is part of the MacTTS (LocalKoreanTTS) project.
See parent README for contribution guidelines.
