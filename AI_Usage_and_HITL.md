# AI Tool Usage & Human-in-the-Loop Documentation

**Project**: AI Interior Concept Board Generator
**Course**: 2026-1 AI & Interior Architecture Design
**Author**: 김지현 / 2021153021

---

## 1. AI Agent 활용 지점 (Where AI was used)

### 1.1 개발 도구 — Claude Code
- 전체 `app.py` (~1,700줄) 구조 설계 및 코드 구현
- Gradio UI 컴포넌트 구성 및 이벤트 체인 연결
- ComfyUI REST API 연동, workflow.json 동적 패치 로직 구현
- 버그 수정 및 반복 디버깅 (포트 충돌, Gradio 6.0 호환성, API 429/503 오류 처리 등)
- 기능 확장 (img2img, Hi-Res Upscale, History/Favorites, Export)

### 1.2 런타임 AI — 앱 내부에서 사용되는 모델
| 모델 | 역할 |
|------|------|
| Gemini 2.5 / 2.0 Flash | 사용자 파라미터 → Design Intent 텍스트 + 이미지 생성 프롬프트 3종 작성 |
| Gemini Vision | 업로드된 레퍼런스 이미지 분석(재료/조명/무드 자동 태깅), 생성 결과 이미지 평가 및 개선안 제시 |
| ComfyUI + FLUX | 텍스트 프롬프트 → 인테리어 이미지 3장 생성 (txt2img / img2img) |
| 4x-UltraSharp | 생성 이미지 업스케일 |
| Ollama (llama3.2) | Gemini 장애 시 텍스트 생성 fallback |
| Pollinations.ai | ComfyUI 미연결 시 이미지 생성 fallback |

---

## 2. Human-in-the-Loop 개입 지점 (Where the human directed/decided)

### 2.1 설계 의사결정 (본인)
- 전체 워크플로우 설계: Input → AI Analysis → Image Generation → Concept Board → Export
- UI 구조 결정: 좌측 입력 패널 / 우측 결과 패널(Concept Board, Prompts, Tags, Images 탭)
- 디자인 파라미터 카테고리 정의: Space Type, Mood, Material, Lighting, Activity, Spatial Quality

### 2.2 프롬프트 엔지니어링 (본인)
- Gemini에게 전달하는 프롬프트 템플릿 직접 설계
  - "Design Intent + 3개 이미지 프롬프트가 동일한 시각적 스타일/색상/재료를 공유해야 한다"는
    일관성 조건을 직접 추가하여 3장의 이미지가 따로 노는 문제 해결
- Evaluate 기능 프롬프트를 "점수 + 평가 + 구체적 개선안 2가지" 형식으로 직접 재설계
  (단순 비평 → 실행 가능한 피드백으로 변경)

### 2.3 반복 검증 및 수정 지시 (본인 → Claude Code)
실제 개발 과정에서 발생한 문제와 본인의 개입 사례:

| 발견한 문제 | 본인의 진단/지시 | 결과 |
|------------|----------------|------|
| Reference 이미지 업로드해도 결과가 안 비슷함 | "img2img가 실제로 적용 안 되는 것 같다" → img2img 파이프라인 구현 요청 | LoadImage+VAEEncode 노드 동적 삽입 구현 |
| Material 이미지가 부정확하게 생성됨 | "재료 이미지가 이상하다, 프롬프트를 더 구체적으로" | 재료별 프롬프트에 구체적 디스크립션 추가 ("no carpet" 등) |
| Atmosphere 이미지가 메인 이미지와 스타일이 동떨어짐 | 원인 분석 후 "3개 프롬프트가 같은 스타일을 공유하도록" 지시 | LLM 프롬프트에 일관성 조건 추가 |
| Pinned board 재접속 시 내용이 안 보임 | 재현 후 "프롬프트/태그/이미지까지 전부 복원되게" 지시 | toggle_pin/load_favorite_entry 데이터 구조 확장 |
| Hi-Res 버튼 누르면 이미지 내용이 바뀜 | "사이즈만 바뀌어야 하는데 내용이 달라진다" 지적 | txt2img 재생성 방식 → 4x-UltraSharp 업스케일 + PIL 리사이즈로 변경 (내용 보존) |
| Gemini 429 / Ollama 500 반복 발생 | 터미널 로그 직접 확인 후 원인(할당량 초과, 한글 경로 문제) 진단 요청 | 듀얼 API 키 + 모델 fallback 체인 구현 |

### 2.4 최종 결과 검증 (본인)
- 매 기능 추가 후 실제 웹 UI에서 직접 실행하여 동작 확인
- 생성된 컨셉보드의 디자인 품질을 Evaluate 기능으로 점검하고, 결과를 바탕으로 추가 개선 방향 결정
- 발표/제출 자료 구성 및 슬라이드별 내용·이미지 배치 결정

---

## 3. 요약

이 프로젝트는 **"AI가 디자인을 대신하는 시스템"이 아니라, 디자이너(본인)가 설계한 워크플로우와
프롬프트 전략 위에서 여러 AI 모델(Gemini, FLUX, Ollama)이 도구로 동작하는 구조**입니다.
Claude Code는 이 시스템을 구현하는 개발 보조 도구로 사용되었으며,
기능의 방향성·문제 진단·우선순위 결정은 모두 본인이 수행했습니다.
