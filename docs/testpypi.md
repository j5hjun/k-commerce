# Python Compatibility and TestPyPI

`.github/workflows/testpypi.yml`은 `dev`·`main` 대상 PR에서 검증하고, `dev`의 VERSION 변경 커밋을 검증한 뒤 TestPyPI에 배포합니다. 일반 PyPI에는 배포하지 않습니다.
수동 실행(`workflow_dispatch`)은 검증만 수행합니다.

## Verification

| Job | 환경 | 통과 조건 |
| --- | --- | --- |
| `source-tests` | Python 3.11, 3.12, 3.13 | `uv sync --locked`, 실제 인터프리터 버전 확인, `pytest -m "not smoke"` 통과 |
| `build` | Python 3.13 | 루트 `k-commerce`의 wheel·sdist 빌드, Twine 메타데이터 검사 |
| `distribution-tests` | Python 3개 × wheel/sdist | 격리된 설치, 의존성 검사, CLI 및 MCP 호출 성공 |
| `compatibility` | 전체 결과 | 앞선 모든 작업 성공; 실패·취소·건너뜀은 통과하지 않음 |
| `publish-testpypi` | `dev`의 미완료 VERSION만 | 보존한 검증 아티팩트를 OIDC로 업로드 |
| `verify-testpypi` | Python 3.11, 3.12, 3.13 | 실제 TestPyPI 파일의 해시 일치 및 wheel 설치·MCP 호출 성공 |

각 matrix는 독립된 Ubuntu 러너에서 실행하며, 한 버전이 실패해도 다른 버전의
검증을 계속합니다. 실제 쿠팡 로그인과 브라우저 조작이 필요한 smoke 테스트는
제외합니다. macOS 브라우저 동작과 실제 모델 호출은 이 워크플로의 검증 대상이 아닙니다.

Python 3.11에서도 타입 보조 기능을 사용할 수 있도록 `typing_extensions`를 직접
의존성으로 선언합니다. 현재 서버는 FastMCP API를 사용하므로 배포 의존성도
`mcp>=1.28,<2`로 제한합니다. 잠금 파일을 사용하지 않는 사용자 설치에서 SDK 2.x가
선택되어 서버 시작이 실패하는 것을 방지하기 위한 범위입니다.

배포 파일은 한 번 빌드하여 모든 설치 검사와 업로드에서 공유합니다.
sdist 검사는 각 Python 버전에서 캐시를 사용하지 않고 wheel을 다시 빌드합니다.
설치는 저장소 밖의 새 가상환경에서 실행하며, 개발용 의존성을 추가하지 않습니다.
설치된 모듈 경로가 해당 가상환경에 속하는지도 확인합니다.

MCP 검사는 설치된 `k-commerce-mcp` 프로세스를 시작하여 초기화, 도구 목록과
`product_detail` 입력 스키마, `get_providers`, 잘못된 상품 URL의 실패 응답,
프로세스 종료까지 확인합니다. 상품 조회 실패에서는 `isError: true`, `success: false`,
`error_code`와 빈 `image_delivery`를 확인하고, JSON 텍스트와 `structuredContent`가
동일하며 제거한 `ocr` 필드가 없는지도 검사합니다. 이미지 변환 모듈이 배포 파일에
포함되는지 확인하고, 실제 이미지 블록 반환·부분 실패·첨부 제한은 소스 테스트에서
모의 HTTP 응답으로 검증합니다.

로그와 JUnit XML은 Actions 아티팩트에 남깁니다. 결과를 확인할 때 실행 환경별
아티팩트와 `compatibility` 검사를 함께 봅니다.
모든 실행 단계는 명시적인 `bash` 셸을 사용하여 GitHub Actions의 `-eo pipefail`을
적용합니다. `tee`로 로그를 저장하더라도 원래 검사 명령의 실패가 작업 실패로 전파됩니다.

## Version and Release PRs

`VERSION`은 실제 배포 버전입니다. 파일 값이 `0.1.3`이면 wheel·sdist·TestPyPI에도
`0.1.3`을 사용합니다. 빌드 중 파일을 임시 변경하거나 개발 접미사를 붙이지 않습니다.
TestPyPI 인덱스를 조회하여 다음 버전을 계산하는 이전 구현은 제거했습니다.

1. 일반 변경이 `dev`에 병합되면 현재 VERSION의 배포 완료 여부를 확인합니다.
2. 이미 배포 완료된 버전 이후의 변경이 있으면 전용 GitHub App 봇이
   `chore/release-version` 브랜치에서 VERSION의 patch를 정확히 1 올립니다.
3. `uv lock`을 실행하고 VERSION과 필요한 uv.lock 변경만 포함한 PR을 `dev`에 엽니다.
   현재 uv는 dynamic workspace 패키지의 버전을 lock에 생략하므로 uv.lock diff가 없을 수도 있습니다.
4. 열린 봇 PR은 하나로 유지하며 dev가 이동하면 최신 dev에서 다시 생성한 커밋으로 갱신합니다.
5. 최신 dev 기반의 봇 PR에 compatibility와 version-policy 검사가 통과하면 봇이
   일반 merge API로 squash 병합합니다. 보호 브랜치 직접 push나 관리자 우회는 사용하지 않습니다.
6. VERSION 변경 커밋을 고정하여 검증·배포합니다. 봇의 버전 커밋 자체는 다음 bump를 유발하지 않습니다.

소유자가 `VERSION=0.2.0`으로 변경하고 필요한 `uv lock` 동기화를 포함하면
`0.2.0`을 그대로 배포합니다. 이후 일반 변경부터 `0.2.1`을 준비합니다.
새 major는 minor·patch를 0으로, 새 minor는 patch를 0으로 시작합니다.
patch 건너뛰기·버전 감소·개발 접미사는 허용하지 않습니다.

### Version authorization

`version-policy.yml`은 `pull_request_target`에서 보호된 기본 브랜치 코드를 실행합니다.
PR 파일은 GitHub API로만 읽고 PR의 코드·워크플로·의존성을 실행하지 않습니다.
미완료 초안 릴리스의 조회를 위해 contents: write 권한이 필요하지만 저장소 내용은 수정하지 않습니다.

- 일반 기여자의 VERSION 변경은 j5hjun의 현재 head에 대한 승인이 필요합니다.
- j5hjun이 작성한 PR은 본인 변경으로 인정합니다. 자기 승인을 요구하지 않습니다.
- 봇은 지정된 App 계정, 같은 저장소의 지정 브랜치, patch +1, VERSION/uv.lock만
  변경, lock 의존성 불변 조건을 모두 만족해야 합니다.
- 소유자의 최신 승인 철회·변경 요청·새 커밋 이후의 이전 승인은 인정하지 않습니다.
- 미완료 배포가 있으면 다음 VERSION 변경은 차단합니다.
- main은 현재 보호된 dev의 버전을 승격하는 PR만 허용합니다. 누적 patch 승격은 허용합니다.

VERSION에 파일 전체 CODEOWNERS 승인을 요구하던 항목은 제거했습니다.
대신 **version-policy를 필수 상태 검사로 설정해야 보호가 강제됩니다.**
워크플로·검사 코드·패키지 빌드 설정은 계속 j5hjun의 CODEOWNERS 보호를 받습니다.
이 정책은 보호 브랜치에 반영할 권한을 제한하며 다른 사람의 브랜치 편집을 막는 기능은 아닙니다.

승인 후 상태 재평가는 컨트롤러의 주기 실행(약 10분, GitHub 스케줄 지연 가능)에서 수행합니다.
즉시 확인하려면 기본 브랜치에서 `Version policy`를 PR 번호와 함께 수동 실행합니다.
CODEOWNERS 및 새 workflow는 대상/기본 브랜치에 병합되어야 활성화됩니다.

### Release state and retries

GitHub의 `testpypi-v<VERSION>` 초안 릴리스는 배포 대기 기록입니다.
body에는 버전과 VERSION이 마지막으로 바뀐 first-parent 커밋을 기록합니다.
이 커밋을 고정하므로 배포 중 일반 변경이 추가되어도 같은 버전에 다른 코드를 넣지 않습니다.
일반 push가 여러 번 몰려 실행이 합쳐지더라도 누락된 버전 커밋을 찾아 배포합니다.

검증된 wheel·sdist·release.json은 게시 전에 단일 `release-bundle.tar` 자산으로 보존합니다.
`release.json`에는 버전·커밋 SHA·파일별 SHA-256이 있습니다. 초안과 아티팩트를
준비한 뒤 OIDC로 TestPyPI에 업로드하고 Python 3개 환경에서 원격 바이트와 설치를 검증합니다.
모든 검증이 통과하면 초안을 완료된 GitHub prerelease로 전환합니다.
GitHub의 prerelease 표시는 테스트 인덱스용임을 나타내며 Python 버전에는 접미사가 없습니다.

- 업로드 작업만 재시도하면 기존 Actions 아티팩트를 사용합니다.
- 전체 실행을 재시도해도 저장된 번들이 있으면 재빌드하지 않고 같은 파일을 복원합니다.
- 번들을 저장하기 전 테스트/빌드가 실패했다면 원래 버전 커밋으로 다시 빌드할 수 있습니다.
- 동일 버전에 다른 커밋·다른 파일을 저장하려 하면 실패합니다.
- 부분 업로드는 기존 파일을 건너뛰고 복구하며 게시 후 해시를 다시 비교합니다.
- 미완료 초안이 있으면 자동으로 다음 버전 PR을 만들거나 병합하지 않습니다.
- 자산이 불완전하거나 배포 파일이 유실되면 자동으로 새 버전을 소비하지 않고 중단합니다.

실패 시 원래 `Python compatibility and TestPyPI` 실행을 재실행합니다.
수동 workflow_dispatch는 검증 전용이며 게시하지 않습니다. 이미 TestPyPI에 일부라도 게시한
릴리스 기록·번들은 삭제하거나 덮어쓰지 않습니다. 게시 전 실패의 기록을 폐기해야 할 경우에도
운영자가 TestPyPI에 파일이 없는 것을 먼저 확인하고 별도 복구해야 합니다.

`dev` 배포 전체를 하나의 concurrency 그룹으로 직렬화합니다. GitHub의 대기 실행은
최신 실행으로 합쳐질 수 있으므로 모든 커밋의 개별 배포를 보장하지 않습니다.
컨트롤러는 별도 그룹에서 직렬화하고, dev가 이동하면 PR 생성·병합을 다음 실행으로 미룹니다.

## GitHub and TestPyPI Setup

1. TestPyPI의 기존 `k-commerce` 프로젝트에서 Publishing 설정을 엽니다.
2. 다음 GitHub Trusted Publisher를 등록합니다.

   | 항목 | 값 |
   | --- | --- |
   | Owner | `j5hjun` |
   | Repository | `k-commerce` |
   | Workflow | `testpypi.yml` |
   | Environment | `testpypi` |

3. GitHub의 `testpypi` Environment에서 배포 허용 브랜치를 `dev`로 제한합니다.
   자동 배포를 위해 수동 승인 대기나 대기 시간을 설정하지 않습니다.
4. `dev` 브랜치 보호의 필수 상태 검사에 `compatibility`와 `version-policy`를 추가합니다.
   두 검사의 제공자는 GitHub Actions로 제한합니다.
   기존 PR·리뷰 보호 규칙은 유지합니다.

TestPyPI API 토큰은 저장하지 않으며, `id-token: write`는 업로드 작업에만 부여합니다.
Trusted Publisher 등록이 없으면 검증은 통과할 수 있지만 업로드는 실패합니다.
외부 액션은 커밋 SHA로 고정하고 uv는 `0.9.25`로 고정합니다.
봇 구성과 활성화 절차는 [Release Bot Setup](release-bot-setup.md)을 참고합니다.

## Local Verification

버전별로 `UV_PYTHON`과 서로 다른 `UV_PROJECT_ENVIRONMENT`를 지정해
`uv sync --locked` 후 `uv run --no-sync python -m pytest -m "not smoke"`를 실행합니다.
빌드는 VERSION을 수정하지 않습니다.

```bash
UV_PYTHON=3.13 python3 scripts/ci/build_release.py --output /tmp/k-commerce-release
python3 scripts/ci/verify_distribution.py --release-dir /tmp/k-commerce-release --python-version 3.11 --format wheel
python3 scripts/ci/verify_distribution.py --release-dir /tmp/k-commerce-release --python-version 3.11 --format sdist
```

출력 폴더는 존재하지 않는 새 경로를 사용합니다. 3.12와 3.13에도 같은 설치 검사를
반복합니다. 게시 후에는 `fetch_testpypi.py`로 배포 파일을 내려받아 같은 검사를 수행합니다.
설치 예시는 Actions의 배포 요약에 정확한 버전과 함께 표시합니다.

## References

- [uv GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [uv package publishing](https://docs.astral.sh/uv/guides/package/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
