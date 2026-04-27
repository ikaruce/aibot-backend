## AI CLI 워크플로우 추가

이 PR은 **{{APP_NAME}}** 이 자동으로 생성한 워크플로우 파일을 추가합니다.

### 추가되는 파일

| 파일 | 역할 |
|------|------|
| `.github/workflows/ai-cli-dispatch.yml` | 이벤트 감지 및 AI CLI 워크플로우 라우팅 |

### 사전 조건

이 워크플로우가 동작하려면 다음 **Repository Secrets / Variables** 를 설정해야 합니다:

| 종류 | 이름 | 설명 |
|------|------|------|
| Secret | `AI_CLI_API_KEY` | AI 도구 API 키 (예: Gemini API 키) |
| Variable | `AI_CLI_APP_NAME` | 댓글에 표시할 앱 이름 (기본값: `{{APP_NAME}}`) |
| Variable | `AI_CLI_SKILL` | PR 리뷰에 사용할 스킬 (기본값: `code-review-commons`) |
| Variable | `AI_CLI_RULES` | 적용할 규칙 목록 (기본값: `code-inspection-common`) |

### 동작 방식

PR을 머지하면 즉시 다음 기능이 활성화됩니다:

- **PR 자동 리뷰**: PR을 열거나 업데이트하면 자동으로 코드 리뷰 댓글이 달립니다.
- **자유 형식 명령**: PR 또는 리뷰 댓글에 `@ai-cli <명령>` 입력 시 AI가 응답합니다.
