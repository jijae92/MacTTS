# Dialog TTS - 대화형 듀엣 TTS 생성기

대본의 화자 라벨(`A:`, `B:` 등)을 자동으로 인식하여 각 화자에게 서로 다른 음성을 적용하고, 하나의 오디오 파일로 병합하는 멀티 스피커 TTS 도구입니다.

## 🚀 NEW: Enhanced Version Available!

**`dialog_tts_enhanced.py`** 는 성능과 품질을 크게 향상시킨 버전입니다:
- ⚡ **2-4배 빠른 합성** (병렬 처리)
- 💾 **10-100배 빠른 재합성** (스마트 캐싱)
- 🎚️ **프로페셔널 오디오 품질** (LUFS 정규화)
- 🔄 **자동 재시도** (네트워크 오류 복구)
- 📊 **실시간 진행률 표시**

👉 **[성능 비교 및 사용법 보기](PERFORMANCE.md)**

```bash
# Enhanced 버전 사용 (추천!)
python dialog_tts_enhanced.py \
  --script samples/dialog.txt \
  --voices A="SunHi,rate=180,pan=-0.3" B="InJoon,rate=170,pan=+0.3" \
  --out podcast.wav \
  --stereo \
  --lufs -16 \
  --workers 3
```

## 주요 기능

- **자동 화자 인식**: `화자명: 대사` 형식을 자동 파싱
- **커스텀 화자 이름**: A, B를 원하는 이름(학생, 전문가 등)으로 매핑
- **GUI 애플리케이션**: 사용하기 쉬운 그래픽 인터페이스 제공
- **Microsoft Edge TTS**: 자연스러운 한국어 음성 (10개 보이스)
- **다중 백엔드 지원**:
  - Microsoft Edge TTS (권장, 최고 품질)
  - macOS 내장 TTS (PyObjC NSSpeechSynthesizer)
  - macOS `say` 명령어 (폴백)
  - Coqui XTTS v2 (선택적, 음성 클로닝 지원)
- **스테레오 패닝**: 화자별로 좌/우 위치 설정 가능
- **음성 커스터마이징**: 속도, 볼륨, 음색 개별 조정
- **지시문 지원**: `[silence=400]`, `[sfx=path.wav]` 등
- **문장 분할**: 자연스러운 호흡을 위한 자동 문장 경계 처리
- **🆕 병렬 합성**: 여러 라인을 동시에 처리 (2-4배 속도 향상)
- **🆕 스마트 캐싱**: 반복 텍스트 자동 재사용
- **🆕 LUFS 정규화**: 프로페셔널한 오디오 레벨링

## 설치

### 1. 필수 요구사항

- macOS 13+ (macOS TTS 사용 시)
- Python 3.8+
- ffmpeg

```bash
# ffmpeg 설치 (macOS)
brew install ffmpeg
```

### 2. Python 패키지 설치

```bash
# 기본 설치 (macOS TTS)
cd dialog-tts
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. XTTS 지원 (선택사항)

```bash
# XTTS v2 음성 클로닝을 사용하려면:
pip install TTS
```

## 사용법

### GUI 애플리케이션 (추천!)

가장 쉬운 방법은 GUI 앱을 사용하는 것입니다:

```bash
# 직접 실행
python dialog_tts_gui.py

# 또는 빌드된 앱 실행
open dist/DialogTTS.app
```

**GUI 기능:**
- 대본 입력창에서 직접 편집
- 화자 이름 커스터마이징 (학생, 전문가 등)
- 음성, 속도, 패닝 조절
- 스테레오/모노 선택
- 실시간 로그 확인

### CLI 사용법

#### 기본 사용법 (macOS 내장 음성)

```bash
python dialog_tts.py \
  --script samples/dialog.txt \
  --speaker-map config/speakers.yaml \
  --out output/dialog.wav \
  --stereo
```

### 인라인 음성 설정

```bash
python dialog_tts.py \
  --script samples/dialog.txt \
  --voices A="ko_KR:Yuna,rate=180,pan=-0.35,gain=0" \
          B="ko_KR:Jinho,rate=170,pan=+0.35,gain=-1" \
  --out output/dialog.wav \
  --stereo
```

### 커스텀 화자 이름 사용 (NEW!)

대본의 A, B를 원하는 이름으로 매핑:

```bash
python dialog_tts.py \
  --script samples/dialog_custom.txt \
  --voices A="ko_KR:Yuna,rate=180,pan=-0.3" \
          B="ko_KR:Jinho,rate=170,pan=+0.3" \
  --speaker-names 학생 전문가 \
  --out output/custom.wav \
  --stereo
```

**동작 방식:**
- 대본에는 여전히 `A:`, `B:` 형식으로 작성
- `--speaker-names` 옵션으로 `A → 학생`, `B → 전문가`로 자동 매핑
- 출력 로그와 처리 과정에서 커스텀 이름 사용

### XTTS v2 사용 (음성 클로닝)

```bash
python dialog_tts.py \
  --script samples/dialog.txt \
  --engine xtts \
  --speaker-map config/speakers_xtts.yaml \
  --out output/dialog.wav \
  --stereo
```

## 대본 형식

### 기본 문법

```
# 주석은 # 으로 시작

A: 안녕하세요. 일정 확인하셨어요?
B: 네, 10시에 스탠드업부터 시작해요.

[silence=400]

A: 그 다음은 보안 점검 보고서 리뷰죠.
B: 맞아요. 성능 테스트도 같이 봐요.
```

### 지원하는 구문

- **화자 라벨**: `Speaker: 대사` (공백 허용, 한글/영문/숫자)
- **전각 콜론**: `Speaker： 대사` (：도 인식)
- **주석**: `# 주석 내용` (무시됨)
- **빈 줄**: 무시됨
- **지시문**:
  - `[silence=밀리초]` - 무음 삽입
  - `[sfx=파일경로 vol=-6 pan=+0.3]` - 효과음 삽입

### 예제

```
A: 안녕하세요!
B: 반갑습니다. 어떻게 도와드릴까요?

[silence=500]

A: 일정 조율이 필요합니다.
B: 네, 언제가 좋으세요?

[sfx=samples/phone_ring.wav vol=-10 pan=0]

A: 잠깐만요, 전화 좀 받을게요.
```

## 화자 매핑 설정

### macOS TTS 설정 (speakers.yaml)

```yaml
A:
  voice_hint: "ko_KR"      # 음성 검색 힌트
  voice_name: "Yuna"       # 특정 음성 이름
  rate_wpm: 180            # 발화 속도 (분당 단어 수)
  gain_db: 0.0             # 볼륨 조정 (dB)
  pan: -0.35               # 스테레오 위치 (-1.0 좌 ~ +1.0 우)
  aliases:                 # 화자 별칭
    - "화자A"
    - "Agent"

B:
  voice_hint: "ko_KR"
  voice_name: "Jinho"
  rate_wpm: 170
  gain_db: -1.0
  pan: +0.35
  aliases:
    - "화자B"
    - "Customer"
```

### XTTS 설정 (speakers_xtts.yaml)

```yaml
A:
  ref_wav: "refs/speaker_A.wav"  # 참조 음성 파일 (6-24초 권장)
  lang: "ko"                      # 언어 코드
  speed: 1.00                     # 속도 배율
  gain_db: 0.0                    # 볼륨 조정
  pan: -0.35                      # 스테레오 위치
  aliases:
    - "화자A"

B:
  ref_wav: "refs/speaker_B.wav"
  lang: "ko"
  speed: 0.98
  gain_db: -1.0
  pan: +0.35
  aliases:
    - "화자B"
```

## CLI 옵션

```
필수 인자:
  --script PATH          대본 파일 경로
  --out PATH            출력 오디오 파일 경로 (WAV/MP3)
  --speaker-map PATH    YAML 화자 설정 파일
  또는
  --voices SPEC [SPEC]  인라인 화자 설정

선택 옵션:
  --engine {mac,xtts}   TTS 엔진 (기본: mac)
  --model-dir PATH      XTTS 모델 디렉토리
  --speaker-names NAME [NAME ...]
                        커스텀 화자 이름 (A→첫번째, B→두번째 순서로 매핑)
                        예: --speaker-names 학생 전문가
  --sr RATE             샘플레이트 Hz (기본: 24000)
  --stereo              스테레오 출력 (패닝 활성화)
  --gap-ms MS           줄 간격 밀리초 (기본: 250)
  --xfade-ms MS         문장 크로스페이드 (기본: 20)
  --breath-ms MS        문장 경계 호흡 (기본: 80)
  --normalize DBFS      정규화 목표 dBFS (기본: -1.0)
  --default-speaker     미등록 화자 폴백
```

## 품질 최적화 팁

### macOS TTS

1. **음성 목록 확인**:
```bash
# macOS에서 사용 가능한 음성 확인
say -v ?
```

2. **한국어 음성 설치**:
   - 시스템 설정 → 손쉬운 사용 → 음성 콘텐츠 → 시스템 음성
   - "Yuna", "Jinho" 등 한국어 음성 다운로드

3. **속도 조정**: `rate_wpm` 값으로 자연스러운 속도 찾기 (150-200 권장)

### XTTS v2

1. **참조 음성 녹음**:
   - 깨끗한 환경에서 6-24초 길이 녹음
   - 배경 소음 최소화
   - 다양한 억양 포함
   - 22050 Hz 샘플레이트 권장

2. **음성 품질 검증**:
```python
from backends.xtts_backend import XTTSBackend
backend = XTTSBackend()
result = backend.validate_reference_audio(Path("ref.wav"))
print(result)
```

### 일반 팁

- 스테레오 패닝으로 화자 구분 강화
- 문장 끝 호흡(`breath_ms`)으로 자연스러움 증가
- 줄 간격(`gap_ms`)으로 대화 리듬 조절

## 테스트

```bash
# 모든 테스트 실행
pytest

# 특정 테스트만 실행
pytest tests/test_parser.py -v

# 커버리지 포함
pytest --cov=. --cov-report=html
```

## 트러블슈팅

### PyObjC 권한 오류

macOS에서 PyObjC 사용 시 권한 문제가 발생할 수 있습니다:
```bash
# 'say' 폴백 사용 (PyObjC 없이)
# requirements.txt에서 pyobjc-framework-Cocoa를 주석 처리
```

### ffmpeg 미설치

```
Error: ffmpeg not found
```

해결:
```bash
brew install ffmpeg
```

### 음성 파일 생성 실패

macOS 음성이 설치되지 않은 경우:
1. 시스템 설정 → 손쉬운 사용 → 음성 콘텐츠
2. 원하는 음성 다운로드

### XTTS 메모리 부족

XTTS는 GPU 메모리를 많이 사용합니다. CPU 모드 강제:
```bash
export CUDA_VISIBLE_DEVICES=""
```

## 프로젝트 구조

```
dialog-tts/
├── dialog_tts.py              # 메인 CLI
├── parser_utils.py            # 대본 파서
├── audio_utils.py             # 오디오 처리
├── backends/
│   ├── mac_nsspeech.py       # PyObjC 백엔드
│   ├── mac_say_cli.py        # say 명령어 백엔드
│   └── xtts_backend.py       # XTTS v2 백엔드
├── config/
│   ├── speakers.yaml         # macOS TTS 화자 설정
│   └── speakers_xtts.yaml    # XTTS 화자 설정
├── samples/
│   └── dialog.txt            # 샘플 대본
├── tests/
│   ├── test_parser.py        # 파서 테스트
│   ├── test_audio.py         # 오디오 테스트
│   └── test_cli_smoke.py     # CLI 스모크 테스트
├── requirements.txt
└── README.md
```

## 라이선스 및 주의사항

### 음성 사용 주의

- **저작권**: 생성된 음성의 저작권과 사용 권한을 확인하세요
- **상업적 사용**: 각 TTS 엔진의 라이선스를 준수하세요
- **음성 도용 금지**: XTTS로 타인의 음성을 무단 복제하지 마세요
- **윤리적 사용**: 딥페이크나 사칭 목적으로 사용하지 마세요

### TTS 엔진 라이선스

- **macOS TTS**: Apple 소프트웨어 사용권 계약 준수
- **Coqui TTS**: MPL 2.0 라이선스

## 기여

버그 리포트나 기능 제안은 이슈로 등록해주세요.

## 빌드 (독립 실행 파일)

### GUI 앱 빌드

```bash
# GUI 앱 빌드 (.app 번들)
pyinstaller --clean dialog_tts_gui.spec

# 빌드된 앱 위치
dist/DialogTTS.app

# 실행
open dist/DialogTTS.app

# Applications 폴더에 설치
cp -R dist/DialogTTS.app /Applications/
```

**GUI 앱 정보:**
- **빌드 크기**: ~97MB
- **형식**: macOS .app 번들
- **포함 내용**: Python 런타임, PySide6, pydub, 모든 백엔드
- **더블클릭 실행**: Finder에서 바로 실행 가능

### CLI 빌드

```bash
# CLI 빌드
pyinstaller --clean dialog_tts.spec

# 빌드된 실행 파일 위치
dist/dialog-tts/dialog-tts

# 실행 예시
./dist/dialog-tts/dialog-tts --script samples/dialog.txt \
  --voices 'A=ko_KR:Yuna,rate=180' 'B=ko_KR:Jinho,rate=170' \
  --out output.wav --stereo
```

**CLI 빌드 정보:**
- **빌드 크기**: ~18MB
- **포함 내용**: Python 런타임, pydub, PyYAML, 모든 백엔드
- **제외 항목**: XTTS (크기 절감을 위해, 필요시 별도 설치)
- **플랫폼**: macOS (Apple Silicon & Intel)

### 런처 스크립트

프로젝트 루트에서 직접 실행:
```bash
./dialog-tts --help
```

## 변경 이력

### v1.2.0 (2024-11-11)
- **NEW**: GUI 애플리케이션 추가! 🎉
  - PySide6 기반 그래픽 인터페이스
  - 화자 이름 입력 필드 (학생, 전문가 등)
  - 음성 설정 (Voice, Speed, Pan)
  - 오디오 옵션 (Stereo, Gap, Sample Rate)
  - 실시간 로그 및 진행 상황 표시
  - macOS .app 번들로 빌드 가능 (~97MB)

### v1.1.0 (2024-11-11)
- **NEW**: `--speaker-names` 옵션 추가 (커스텀 화자 이름 매핑)
  - 대본의 A, B를 원하는 이름으로 자동 매핑 (예: 학생, 전문가)
  - 순서대로 매핑 (A→첫번째, B→두번째)
- 샘플 대본 추가 (`samples/dialog_custom.txt`)

### v1.0.0 (2024-11-11)
- 초기 릴리스
- macOS NSSpeechSynthesizer 백엔드
- macOS `say` CLI 백엔드
- XTTS v2 백엔드
- 화자 자동 인식 파서
- 스테레오 패닝 지원
- 지시문 시스템 (silence, sfx)
- PyInstaller 빌드 지원
