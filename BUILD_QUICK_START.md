# 빠른 빌드 가이드

> ⚠️ **중요:** 이 빌드 프로세스는 **macOS에서만** 실행 가능합니다.
> 현재 Linux/Windows 환경에서는 macOS 앱을 빌드할 수 없습니다.

## 🚀 5분 안에 빌드하기

### 1단계: 환경 준비 (최초 1회)

```bash
# ffmpeg 설치
brew install ffmpeg

# Python 의존성 설치
pip install pyinstaller PySide6 edge-tts pydub PyYAML pyloudnorm
```

### 2단계: 빌드 실행

#### 메인 GUI 앱 빌드

```bash
cd /path/to/MacTTS
./build_macos.sh
```

완료 후:
- 앱 위치: `dist/localkoreantts-gui/LocalKoreanTTS.app`
- 설치: `cp -R dist/localkoreantts-gui/LocalKoreanTTS.app /Applications/`

#### Dialog TTS GUI 앱 빌드

```bash
cd /path/to/MacTTS/dialog-tts
./build_dialog_tts_gui.sh
```

완료 후:
- 앱 위치: `dist/DialogTTS.app`
- 설치: `cp -R dist/DialogTTS.app /Applications/`

### 3단계: 실행

Spotlight에서 검색:
- "LocalKoreanTTS" - 메인 GUI
- "DialogTTS" - Dialog TTS GUI

## 🔧 수동 빌드 (스크립트 없이)

### 메인 GUI

```bash
cd /path/to/MacTTS
python -m PyInstaller --clean --noconfirm mac_app.spec
open dist/localkoreantts-gui/LocalKoreanTTS.app
```

### Dialog TTS GUI

```bash
cd /path/to/MacTTS/dialog-tts
python -m PyInstaller --clean --noconfirm dialog_tts_gui.spec
open dist/DialogTTS.app
```

## 📝 빌드 체크리스트

빌드 전 확인사항:

- [ ] macOS 13.0+ 사용 중
- [ ] Python 3.11+ 설치됨
- [ ] ffmpeg 설치됨 (`brew install ffmpeg`)
- [ ] PyInstaller 설치됨 (`pip install pyinstaller`)
- [ ] PySide6 설치됨 (`pip install PySide6`)
- [ ] edge-tts 설치됨 (`pip install edge-tts`)
- [ ] 최신 코드로 업데이트됨 (`git pull`)

## ⚡ 빠른 트러블슈팅

### 문제: "command not found: pyinstaller"

```bash
pip install pyinstaller
```

### 문제: "No module named 'PySide6'"

```bash
pip install PySide6
```

### 문제: 앱이 실행되지 않음

```bash
# Gatekeeper 속성 제거
xattr -cr dist/localkoreantts-gui/LocalKoreanTTS.app
```

### 문제: 빌드 스크립트 실행 권한 오류

```bash
chmod +x build_macos.sh
chmod +x dialog-tts/build_dialog_tts_gui.sh
```

## 📚 상세 가이드

더 자세한 빌드 옵션, 코드 서명, 배포 패키지 생성 등은 [BUILD.md](BUILD.md)를 참조하세요.

## 🆘 도움이 필요하신가요?

- 📖 [전체 빌드 가이드](BUILD.md)
- 🐛 [Issues 페이지](https://github.com/your-org/MacTTS/issues)
- 💬 [Discussions](https://github.com/your-org/MacTTS/discussions)

---

**빌드 시간:** 약 2-5분 (시스템 성능에 따라)
**앱 크기:** 150-200 MB (메인 GUI), 120-150 MB (Dialog TTS)
**빌드 환경:** macOS 전용
