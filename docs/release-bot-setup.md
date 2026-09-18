# Release Bot Setup

이 절차는 소유자 `j5hjun`이 최초 한 번 수행합니다. 현재 저장소에는 릴리스 App 설정이
없으므로 구현을 병합해도 봇 PR 생성은 설정 전까지 비활성화됩니다.
일반 PR 검증과 VERSION 커밋의 TestPyPI 배포는 App 없이도 동작합니다.

## 1. Create and install a dedicated GitHub App

GitHub Settings → Developer settings → GitHub Apps → New GitHub App에서 만듭니다.

- 이름: 고유한 릴리스 전용 이름 (예: `k-commerce-release-bot`)
- Homepage URL: `https://github.com/j5hjun/k-commerce`
- Webhook: 비활성화 (이 구현은 GitHub Actions 이벤트를 사용)
- 설치 범위: 본인 계정만, 설치 대상 저장소는 `k-commerce`만 선택
- Repository permissions:
  - Contents: Read and write — 봇 브랜치 커밋 및 보호 규칙을 따르는 PR 병합
  - Pull requests: Read and write — PR 생성·갱신·조회
  - Checks: Read-only — 최신 compatibility 결과 확인
  - Metadata: Read-only — 기본 권한
- Administration·Workflows 우회 권한이나 보호 브랜치 bypass는 부여하지 않습니다.

App을 만든 뒤 설치하고 private key를 발급받습니다. 비밀키를 채팅·저장소·PR에 붙이지 않습니다.

## 2. Configure Actions variables and secret

Repository Settings → Secrets and variables → Actions에서 설정합니다.

| 종류 | 이름 | 값 |
| --- | --- | --- |
| Variable | `RELEASE_APP_ID` | App 설정 화면의 숫자 App ID |
| Variable | `RELEASE_BOT_LOGIN` | 실제 App slug에 `[bot]`을 붙인 계정 이름 |
| Secret | `RELEASE_APP_PRIVATE_KEY` | 발급받은 PEM private key 전체 |

App 생성 후 표시되는 slug를 사용합니다. 예시 이름을 그대로 추정하지 않습니다.
CLI로 등록할 때도 key를 인자로 넣거나 출력하지 말고 파일에서 읽습니다.

```bash
gh variable set RELEASE_APP_ID --body '<App ID>'
gh variable set RELEASE_BOT_LOGIN --body '<app-slug>[bot]'
gh secret set RELEASE_APP_PRIVATE_KEY < /absolute/path/to/private-key.pem
```

`GITHUB_TOKEN`으로 봇 PR을 작성하면 후속 PR/push workflow의 자동 실행이 제한될 수 있어
전용 App 토큰을 사용합니다. 토큰은 실행 중 생성하고 액션 종료 시 폐기합니다.
버전 정책 status는 일관되게 GitHub Actions 토큰으로 게시합니다.

## 3. Activate required checks after merging the implementation

새 `version-policy.yml`은 기본 브랜치 `dev`에 있어야 실행됩니다.
이 구현 PR을 먼저 검토·병합한 뒤 다음을 수행합니다. 기존 PR을 자동 병합하지 않습니다.

1. `Version policy`를 기본 브랜치에서 열린 PR 번호로 수동 실행해
   `version-policy` status가 생성되는지 확인합니다.
2. `dev`와 `main`의 보호 규칙에서 `compatibility`와 `version-policy`를 필수 검사로 지정합니다.
   제공자는 GitHub Actions로 제한하고 최신 대상 브랜치 기준 검사를 유지합니다.
3. 기존 CODEOWNERS 리뷰·기존 승인 무효화·관리자 규칙 적용을 유지합니다.
   VERSION 자체에는 CODEOWNERS 항목을 다시 추가하지 않습니다. 추가하면 봇 patch도
   소유자 리뷰를 기다려 자동 병합되지 않을 수 있습니다.
4. GitHub Actions의 정책 검사와 컨트롤러가 활성화되었는지 확인합니다.
   컨트롤러는 직접 merge API를 사용하므로 저장소의 별도 Allow auto-merge 설정은 필요 없습니다.
5. main에도 워크플로·CODEOWNERS 변경을 정상 승격합니다.

이 PR은 저장소 보호 설정을 자동으로 완화하거나 신규 필수 검사를 사전에 강제하지 않습니다.
새 워크플로가 없는 상태에서 필수로 지정하면 현재 PR까지 병합할 수 없기 때문입니다.
**필수 검사 활성화 전에는 숫자별 버전 권한 정책이 강제된 상태가 아닙니다.**

## 4. Verify one full cycle

- 현재 VERSION은 `0.1.1`입니다. 초기 구현 병합은 기존 `0.1.0`에서의 VERSION 변경을
  포함하므로 `0.1.1`을 그대로 배포합니다. 인덱스나 GitHub 릴리스 기록과 충돌하면 먼저 확인합니다.
- VERSION 변경 없이 일반 PR을 dev에 병합합니다.
- 봇이 VERSION `0.1.1 → 0.1.2` PR을 생성하는지 확인합니다.
- patch +1 외 변경이 없고 두 필수 검사가 성공한 뒤 봇이 병합하는지 확인합니다.
- `testpypi-v0.1.2` 초안에 번들이 보존되고 TestPyPI `0.1.2` 검증 후 완료되는지 확인합니다.
- 버전 커밋만으로 `0.1.3` PR이 연쇄 생성되지 않는지 확인합니다.
- App 설정은 배포·병합 권한을 활성화하므로 이 확인은 설정 완료 후 실제 운영 단계에서 수행합니다.

실패 시 보호 규칙을 우회하지 않고 Actions 로그를 확인합니다. App이 없거나 private key가
설정되지 않은 경우, CI 통과와 별개로 자동 PR 생성·병합은 검증 완료로 간주하지 않습니다.

## References

- [Create GitHub App tokens in Actions](https://github.com/actions/create-github-app-token)
- [GITHUB_TOKEN event behavior](https://docs.github.com/en/enterprise-cloud@latest/actions/concepts/security/github_token)
- [Workflow events and default-branch requirements](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
