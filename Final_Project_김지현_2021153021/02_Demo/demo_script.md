# 데모 영상 스크립트 (예상 3~5분)

화면 녹화: `Win + Shift + S` (캡처) 또는 `Win + G` (Xbox Game Bar 녹화) 사용.
브라우저에서 `http://localhost:7860` (또는 gradio.live 링크) 띄운 상태로 진행.

---

## 0. 인트로 (10초)
> "안녕하세요, AI Interior Concept Board Generator 데모입니다.
> 공간 유형과 디자인 파라미터를 입력하면 AI가 컨셉보드를 자동 생성해주는 웹 앱입니다."

화면: 메인 페이지 전체를 한 번 보여주기 (좌측 입력 패널 + 우측 결과 패널)

---

## 1. 파라미터 입력 (30~40초)
> "먼저 왼쪽에서 공간 유형과 무드를 선택합니다. 저는 '도서관(Library)'과 '차분한(Calm)' 무드를 선택하겠습니다."

화면:
- `Space Type` → Library 선택
- `Mood` → Calm 선택
- `Material Palette`, `Lighting`, `Activities`, `Spatial Quality` 체크박스에서 2~3개씩 선택
  (예: Wood, Stone / Natural Light / Reading / Cozy)

> "Custom Keywords에 자연어로 원하는 분위기를 추가로 입력할 수도 있습니다."

- `Custom Keywords`에 "따뜻한 우드 톤의 조용한 도서관, 바이오필릭 요소" 같은 문장 입력

---

## 2. (선택) AI 자동입력 & 레퍼런스 이미지 업로드 (20~30초)
> "키워드만 입력하고 'AI 자동입력' 버튼을 누르면, Gemini가 적절한 파라미터를 자동으로 채워줍니다."

- `✨ AI 자동입력` 버튼 클릭 → 파라미터가 자동으로 채워지는 것 보여주기

> "또는 레퍼런스 이미지를 업로드하면, Gemini Vision이 이미지를 분석해서 재료/조명/무드를 자동으로 태깅합니다."

- (선택) Reference Images 아코디언 열고 이미지 업로드 → 자동 태깅되는 모습

---

## 3. 컨셉 생성 (Generate Concept) (30~40초)
> "이제 'Generate Concept' 버튼을 누르면, Gemini가 디자인 의도(Design Intent)와
> 이미지 생성 프롬프트 3종(메인 뷰, 재료 디테일, 분위기)을 작성하고,
> ComfyUI + FLUX 모델이 이미지를 생성합니다."

- `Generate Concept ✶` 클릭
- 로딩 중 화면 보여주기 (버튼이 "Generating…"으로 바뀌는 부분)
- 생성 완료 후 **Concept Board 탭** 보여주기:
  - Design Intent 문장
  - 컬러 팔레트
  - 재료 스와치
  - 이미지 3장 (Main View / Material Detail / Atmosphere)

---

## 4. 프롬프트 & 태그 확인 (15~20초)
> "Prompts 탭에서는 실제로 이미지 생성에 사용된 영문 프롬프트 3개를 확인할 수 있고,
> Tags & Statement 탭에서는 해시태그와 한국어 컨셉 설명을 볼 수 있습니다."

- `📝 Prompts` 탭 클릭 → 3개 프롬프트 보여주기
- `🏷️ Tags & Statement` 탭 클릭 → 해시태그 + 한국어 설명 보여주기

---

## 5. 이미지 품질 평가 (Evaluate) (20~30초)
> "Images 탭에서 'Evaluate Images' 버튼을 누르면, Gemini Vision이 각 이미지를
> 평가하고 점수와 구체적인 개선 방안을 제시해줍니다."

- `🖼️ Images` 탭 클릭
- `🔍 Evaluate Images (Gemini)` 클릭
- 결과 (Score / Assessment / Improvements) 보여주기

---

## 6. Hi-Res Upscale (15~20초)
> "원하는 이미지의 사이즈를 선택하고 'Re-generate Hi-Res'를 누르면,
> 이미지 내용은 그대로 유지한 채 4x-UltraSharp 업스케일과 리사이즈로 화질/크기만 개선됩니다."

- Size 드롭다운에서 "1024x1024" 선택
- `⬆ Re-generate Hi-Res` 클릭 → 업스케일된 이미지 보여주기

---

## 7. History / Favorites / Export (20~30초)
> "생성 결과는 History에 자동 저장되고, 마음에 드는 컨셉은 Pin해서 즐겨찾기에 보관할 수 있습니다.
> 그리고 PNG나 PDF로 내보내서 발표 자료에 바로 사용할 수 있습니다."

- `⭐ Pin` 클릭 → Favorites 드롭다운에 추가되는 것 보여주기
- `History` 드롭다운에서 방금 생성한 항목 선택 → 그대로 복원되는 것 보여주기
- `⬇ Export as PDF` 클릭 → 다운로드되는 파일 보여주기

---

## 8. (선택) Admin 패널 (15초)
> "관리자 모드에서는 API 연결 상태, 일별 사용량, Gemini 쿼터 잔여량 등을
> 한눈에 확인할 수 있습니다."

- 좌측 하단 "🔐 Admin Panel" 아코디언 열기 → 비밀번호 입력 → 상태/사용량 보여주기

---

## 9. 마무리 (10초)
> "이상으로 AI Interior Concept Board Generator 데모를 마칩니다. 감사합니다."

---

### 녹화 팁
- 마우스 움직임을 천천히, 클릭 전에 잠깐 멈췄다가 클릭하면 시청자가 따라가기 편함
- 로딩 시간이 긴 구간(이미지 생성, Evaluate)은 영상 편집 시 배속(2~4x) 처리 추천
- 음성 내레이션이 어렵다면, 위 멘트를 자막으로 추가해도 충분함
