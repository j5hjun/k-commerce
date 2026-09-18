# Python Compatibility and TestPyPI

`.github/workflows/testpypi.yml`은 `dev` 대상 PR에서 검증하고, `dev`에 병합된
커밋을 다시 검증한 뒤 TestPyPI에 배포합니다. 일반 PyPI에는 배포하지 않습니다.
수동 실행(`workflow_dispatch`)은 검증만 수행합니다.

## Verification

| Job | 환경 | 통과 조건 |
| --- | --- | --- |
| `source-tests` | Python 3.11, 3.12, 3.13 | `uv sync --locked`, 실제 인터프리터 버전 확인, `pytest -m "not smoke"` 통과 |
| `build` | Python 3.13 | 루트 `k-commerce`의 wheel·sdist 빌드, Twine 메타데이터 검사 |
| `distribution-tests` | Python 3개 × wheel/sdist | 격리된 설치, 의존성 검사, CLI 및 MCP 호출 성공 |
| `compatibility` | 전체 결과 | 앞선 모든 작업 성공; 실패·취소·건너뜀은 통과하지 않음 |
| `publish-testpypi` | `dev` push만 | 검증한 아티팩트를 OIDC로 업로드 |
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

## Version and Retries

`VERSION`은 배포 버전 자체가 아니라 소유자가 선택하는 릴리스 계열과 최솟값입니다.
현재 값 `0.1.1`은 최초 자동 배포의 하한이며, 자동화가 파일을 커밋하거나 수정하지 않습니다.
minor·major 변경은 `@j5hjun`이 `VERSION`을 변경하여 결정합니다.
변경 시 `uv lock`으로 워크스페이스 패키지 버전도 동기화합니다.

CI는 TestPyPI 프로젝트 JSON API의 전체 `releases`를 읽고 다음 patch를 계산합니다.
정식 버전과 `.devN` 버전 모두 patch를 사용한 것으로 취급합니다. `feat`를 포함해도
자동으로 minor·major를 올리지 않습니다. 현재 배포 대상은 TestPyPI뿐이며, 향후 PyPI를
추가할 때는 두 인덱스의 기준과 정식 승격 정책을 별도로 정의해야 합니다.

| VERSION | TestPyPI의 가장 높은 배포 버전 | 다음 빌드 버전 예시 |
| --- | --- | --- |
| `0.1.1` | `0.1.0` | `0.1.1.dev42001` |
| `0.1.1` | `0.1.2.dev42001` | `0.1.3.dev43001` |
| `0.2.0` | `0.1.3.dev43001` | `0.2.0.dev44001` |
| `0.2.0` | `0.2.0.dev44001` | `0.2.1.dev45001` |

- 선택한 기준 버전이 기존 배포보다 높으면 그 기준 버전부터 시작합니다.
- 같은 major·minor이면 기존 최고 patch에 1을 더합니다.
- 이미 배포된 계열보다 낮은 major·minor는 오류로 처리합니다.
- 조회 실패·잘못된 응답·지원하지 않는 버전 형식에서는 추측하여 배포하지 않고 실패합니다.
- yanked·부분 업로드·파일 목록이 빈 버전도 재사용하지 않습니다. 배포 기록을 삭제하면
  계산 기준을 잃으므로 TestPyPI 릴리스를 삭제하지 않습니다.

개발 접미사는 기존의 `.dev{run_id * 1000 + run_attempt}`를 유지합니다.
시도 번호는 1~999만 허용합니다. PR과 수동 실행은 버전을 계산하고 검증만 하므로
patch를 소비하지 않습니다. PR의 미리보기 버전은 실제 병합 시의 배포 버전과 다를 수 있습니다.

`dev` push 실행은 버전 조회부터 게시 후 검증까지 같은 concurrency 그룹으로 직렬화하고,
실행 중인 배포를 새 push가 취소하지 않습니다. GitHub concurrency는 FIFO 대기열이 아니므로
대기 중인 여러 push는 최신 실행으로 대체될 수 있습니다. 모든 커밋의 개별 배포를 보장하지는
않지만, 동시에 같은 patch를 선택하는 것은 방지합니다. 수동 업로드는 이 잠금에 참여하지
않으므로 이 워크플로를 유일한 게시자로 운영합니다.

빌드 중에만 `VERSION`을 변경하고 성공·실패와 관계없이 원래 값으로 복원합니다.
`release.json`에는 실제 배포 버전, 커밋 SHA, 두 파일의 SHA-256을 기록합니다.

실패한 업로드 작업만 재실행하면 이전 빌드 아티팩트와 버전을 재사용합니다.
`skip-existing`은 부분 업로드 재시도를 허용하기 위한 설정이며, 업로드 후 검사에서
서버 메타데이터와 실제 다운로드한 바이트가 원래 해시와 일치하는지 모두 확인합니다.
전체 워크플로를 재실행하면 인덱스를 다시 조회하고 새 개발 버전을 빌드합니다.
이전 버전이 일부라도 게시되었다면 다음 patch를 사용합니다. 게시 이후 검증이 실패해도
이미 업로드된 파일을 자동 삭제하지 않습니다.

### VERSION ownership

`.github/CODEOWNERS`는 `VERSION`, 소유권 설정, CI 스크립트·워크플로 및 패키지 빌드
설정을 `@j5hjun`에게 지정합니다. 다른 사람이 브랜치에서 파일을 편집하는 것을 막는 것이
아니라, 보호 브랜치에 반영하기 위한 소유자 승인을 요구합니다.

`dev`와 `main`에서 코드 소유자 리뷰 필수 및 새 커밋 후 기존 승인 무효화를 유지합니다.
CODEOWNERS는 PR의 대상 브랜치에 있는 파일을 사용하므로 `dev`에 병합된 뒤 후속 PR부터
적용되며, `main`에서도 적용하려면 해당 파일을 승격해야 합니다.
본인이 작성한 PR은 자기 승인할 수 없으므로 GitHub의 병합 가능 상태를 확인하고,
추가 승인이 요구될 경우 별도 PR 작성자나 명시적으로 정한 관리자 절차를 사용합니다.
이 변경은 보호 규칙을 완화하거나 우회 권한을 추가하지 않습니다.

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
4. `dev` 브랜치 보호의 필수 상태 검사에 `compatibility`를 추가합니다.
   기존 PR·리뷰 보호 규칙은 유지합니다.

API 토큰을 저장하지 않으며, `id-token: write`는 업로드 작업에만 부여합니다.
Trusted Publisher 등록이 없으면 검증은 통과할 수 있지만 업로드는 실패합니다.
외부 액션은 커밋 SHA로 고정하고 uv는 `0.9.25`로 고정합니다.

## Local Verification

버전별로 `UV_PYTHON`과 서로 다른 `UV_PROJECT_ENVIRONMENT`를 지정해
`uv sync --locked` 후 `uv run --no-sync python -m pytest -m "not smoke"`를 실행합니다.
버전별 검증은 빌드의 일시적인 `VERSION` 변경과 겹치지 않게 실행합니다.

```bash
UV_PYTHON=3.13 python3 scripts/ci/build_release.py --resolve-testpypi --development --run-id 42 --attempt 1 --output /tmp/k-commerce-release
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
