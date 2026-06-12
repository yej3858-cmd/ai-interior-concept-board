# AI Interior Concept Board Generator

인테리어 디자인 초기 컨셉보드를 자동 생성하는 웹 기반 AI 프로토타입입니다.
공간 유형, 무드, 재료, 조명, 활동 등의 파라미터(또는 레퍼런스 이미지)를 입력하면
Gemini API가 디자인 의도(Design Intent)와 이미지 생성 프롬프트를 만들고,
ComfyUI(FLUX 모델)가 컨셉 이미지 3장을 생성하여 컨셉보드를 자동 구성합니다.

2026-1 AI & Interior Architecture Design — 김지현 / 2021153021

---

## 주요 기능

- **파라미터 기반 입력**: Space Type, Mood, Material, Lighting, Activity, Spatial Quality, Custom Keywords
- **레퍼런스 이미지 업로드 + 자동 분석**: Gemini Vision이 재료/조명/무드를 자동 태깅
- **AI 컨셉 생성**: Gemini 2.5 Flash가 Design Intent 문장과 이미지 프롬프트 3종(Main View / Material Detail / Atmosphere) 생성
- **AI 이미지 생성**: ComfyUI + FLUX 모델 기반, workflow.json을 런타임에 동적 패치
- **Reference img2img**: 업로드 이미지를 LoadImage + VAEEncode 노드로 주입, Denoise로 반영 강도 조절
- **이미지 품질 평가**: Gemini Vision이 생성 이미지를 점수화하고 구체적 개선안 제시
- **Hi-Res Upscale**: 4x-UltraSharp 모델로 화질 개선 + 사이즈 변경 (이미지 내용 유지)
- **컨셉보드 자동 구성**: Design Intent + 이미지 3장 + 컬러 팔레트 + 재료 스와치 + 태그 + 레퍼런스 이미지
- **History / Favorites**: 생성 결과 자동 저장, Pin으로 즐겨찾기
- **Export**: PNG / PDF 내보내기
- **Fallback 구조**: Gemini → Ollama (LLM), ComfyUI → Pollinations.ai (이미지 생성)

---

## 기술 스택

| 구성 | 기술 |
|------|------|
| Web UI | Gradio 6.x |
| 텍스트 생성 | Gemini 2.5 / 2.0 Flash API (Ollama fallback) |
| 이미지 분석 | Gemini Vision API |
| 이미지 생성 | ComfyUI + FLUX (Pollinations.ai fallback) |
| 업스케일 | 4x-UltraSharp via ComfyUI |
| 언어 | Python ~1,700 lines |
| 개발 도구 | Claude Code |

---

## 실행 방법

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정 (.env)
```
GEMINI_API_KEY=your_key_here
GEMINI_API_KEY_2=optional_second_key
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### 3. 실행
```bash
python app.py
```
또는 Windows에서 `run.bat` 더블클릭 (git pull → 실행 → 브라우저 자동 오픈)

### 4. ComfyUI 연동 (선택)
- ComfyUI를 `http://127.0.0.1:8188` 에서 실행
- 프로젝트 루트에 `comfyui_workflow.json`, `Upscale.json` 배치
- 앱 UI에서 "FLUX via ComfyUI" 체크 + Server URL 입력

---

## 워크플로우

1. Reference Image Upload (선택)
2. Gemini Vision 자동 태깅 (materials / lighting / mood)
3. 파라미터 선택 + Custom Keywords 입력
4. Generate Concept 클릭
5. Gemini API → Design Intent + 프롬프트 3종 생성
6. ComfyUI FLUX → 이미지 3장 생성 (Main / Material / Atmosphere)
7. 컨셉보드 자동 구성
8. Image Upscale (선택)
9. Pin 저장 / History 확인
10. PNG / PDF Export

---

## AI Agent 활용 및 Human-in-the-Loop

본 프로젝트의 AI 활용 방식과 개발자 개입 지점은
[`AI_Usage_and_HITL.md`](./AI_Usage_and_HITL.md) 문서에 정리되어 있습니다.
