# MacTTS 빠른 시작 가이드

## 🚀 설치 및 실행 (5분 안에!)

### 1단계: 필수 요구사항 확인

```bash
# Python 버전 확인 (3.10 이상 필요)
python3 --version

# ffmpeg 설치 (TTS 음성 생성에 필수!)
brew install ffmpeg
```

### 2단계: MacTTS 설치

```bash
# MacTTS 디렉토리로 이동
cd ~/MacTTS  # 또는 실제 MacTTS 경로

# 모든 의존성 설치 (한 번만)
pip install -e .
```

### 3단계: 진단 실행 (문제 확인)

```bash
# 모든 것이 제대로 설치되었는지 확인
python diagnose.py
```

**예상 출력:**
```
✓ ffmpeg: OK
✓ pydub: OK
✓ tts_engines: OK
✓ dialog_tts: OK
✓ gui: OK

✓ 모든 검사 통과!
```

### 4단계: GUI 실행

```bash
# 방법 1: 모듈로 실행
python -m localkoreantts.gui

# 방법 2: 직접 실행
python gui_entry.py

# 방법 3: 명령어 사용
localkoreantts-gui
```

---

## ❌ 문제 해결

### 문제 1: "사인파 소리만 들려요"

**원인:** ffmpeg가 설치되지 않았거나 인식되지 않음

**해결:**
```bash
# 1. ffmpeg 설치
brew install ffmpeg

# 2. 설치 확인
which ffmpeg
ffmpeg -version

# 3. GUI 재시작
python -m localkoreantts.gui
```

### 문제 2: "대화 형식 탭이 안 보여요"

**원인:** dialog-tts 모듈을 찾을 수 없음

**해결:**
```bash
# 1. 진단 실행
python diagnose.py

# 2. dialog-tts 확인
ls -la dialog-tts/dialog_tts.py

# 3. 없으면 git 서브모듈 업데이트
git submodule update --init --recursive

# 4. GUI 재시작
python -m localkoreantts.gui
```

### 문제 3: "ModuleNotFoundError: No module named 'PySide6'"

**원인:** 필요한 패키지가 설치되지 않음

**해결:**
```bash
# MacTTS 디렉토리에서
pip install -e .

# 또는 수동으로
pip install PySide6 edge-tts gtts pydub numpy soundfile sounddevice
```

### 문제 4: "가상환경 문제"

**원인:** 다른 프로젝트의 가상환경 사용 중

**해결:**
```bash
# 1. 올바른 디렉토리로 이동
cd ~/MacTTS

# 2. 가상환경 비활성화 (필요시)
deactivate

# 3. 시스템 Python 사용 또는 새 가상환경 생성
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 4. GUI 실행
python -m localkoreantts.gui
```

---

## 🔍 진단 도구 사용법

```bash
# 모든 문제를 자동으로 확인
python diagnose.py
```

**진단 항목:**
- ✓ FFmpeg 설치 및 경로
- ✓ pydub 설정
- ✓ TTS 엔진 (edge-tts, gtts)
- ✓ dialog-tts 모듈
- ✓ GUI 의존성 (PySide6)

---

## 📦 앱 빌드 (배포용)

```bash
# 1. ffmpeg 설치 확인
brew install ffmpeg

# 2. 빌드 스크립트 실행
./build_macos.sh

# 3. 앱 실행
open dist/localkoreantts-gui/LocalKoreanTTS.app

# 4. Applications에 설치
cp -R dist/localkoreantts-gui/LocalKoreanTTS.app /Applications/
```

빌드된 앱은 ffmpeg를 포함하여 독립 실행 가능합니다!

---

## ✅ 기능 확인 체크리스트

GUI를 실행한 후:

- [ ] 세 개의 탭이 보임: 🎤 혼자 말하기, 💬 대화 형식, ⚙️ 설정
- [ ] Log에 "✓ FFmpeg found" 메시지 표시
- [ ] 텍스트 입력 후 "Generate Audio" 클릭
- [ ] 실제 한국어 음성이 생성됨 (사인파 아님!)
- [ ] 대화 형식 탭에서 두 화자 대화 가능

---

## 🎯 다음 단계

모든 것이 작동한다면:

1. **혼자 말하기**: 간단한 텍스트로 TTS 테스트
2. **대화 형식**: A:/B: 형식으로 대화 생성
3. **설정**: 모델 경로, ffmpeg 경로 확인
4. **빌드**: 독립 실행 앱 만들기 (`./build_macos.sh`)

문제가 있다면 `python diagnose.py`를 실행하세요!
