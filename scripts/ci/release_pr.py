"""Reconcile a single bot patch PR from the protected dev checkout."""

import os
from pathlib import Path
import subprocess

from scripts.ci.github_api import api, pages, repository
from scripts.ci.release_state import record_for, record_metadata, version_commit
from scripts.ci.version_policy import bump_patch, check_pr, lock_only_versions

BRANCH = "chore/release-version"


def ready_to_merge(pr, dev_sha):
    repo = repository()
    head = pr["head"]["sha"]
    commit = api(f"repos/{repo}/git/commits/{head}")
    if [p["sha"] for p in commit["parents"]] != [dev_sha]:
        return False
    checks = api(f"repos/{repo}/commits/{head}/check-runs?per_page=100")["check_runs"]
    compatible = [c for c in checks if c["name"] == "compatibility" and c["app"]["slug"] == "github-actions"]
    return bool(compatible) and max(compatible, key=lambda c: c["id"])["conclusion"] == "success"


def main():
    repo = repository()
    bot = os.environ["RELEASE_BOT_LOGIN"]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if api(f"repos/{repo}/git/ref/heads/dev")["object"]["sha"] != head:
        print("dev moved; next reconciliation will use the new head")
        return
    prs = pages(f"repos/{repo}/pulls?state=open&base=dev")
    for pr in prs:
        # Refresh owner approvals as well, using only API data (no PR checkout).
        check_pr(pr["number"], bot)
    candidates = [p for p in prs if p["head"]["ref"] == BRANCH and p["head"]["repo"]["full_name"] == repo]
    if len(candidates) > 1 or any(p["user"]["login"] != bot for p in candidates):
        raise ValueError("Reserved release branch has a non-bot or duplicate PR")
    current = candidates[0] if candidates else None
    value = Path("VERSION").read_text().strip()
    record = record_for(value)
    release_commit = version_commit()
    if not record or record["draft"] or record_metadata(record)["commit"] != release_commit:
        print("Waiting for current VERSION to finish publication")
        return
    if head == release_commit:
        if current:
            api(f"repos/{repo}/pulls/{current['number']}", "PATCH", {"state": "closed"})
        print("No changes since the release commit")
        return
    if current and ready_to_merge(current, head):
        if not check_pr(current["number"], bot):
            raise ValueError("Version policy rejected the bot PR")
        result = api(f"repos/{repo}/pulls/{current['number']}/merge", "PUT", {
            "sha": current["head"]["sha"], "merge_method": "squash",
            "commit_title": f"chore: release {bump_patch(value)}",
        })
        if not result.get("merged"):
            raise RuntimeError("Branch protection has not allowed the release PR to merge")
        return
    if current:
        parents = api(f"repos/{repo}/git/commits/{current['head']['sha']}")["parents"]
        if [p["sha"] for p in parents] == [head]:
            print("Waiting for the current bot PR checks")
            return
    new = bump_patch(value)
    old_lock = Path("uv.lock").read_text()
    Path("VERSION").write_text(new + "\n")
    subprocess.run(["uv", "lock"], check=True)
    new_lock = Path("uv.lock").read_text()
    lock_only_versions(old_lock, new_lock, value, new)
    tree = api(f"repos/{repo}/git/trees", "POST", {
        "base_tree": api(f"repos/{repo}/git/commits/{head}")["tree"]["sha"],
        "tree": [{"path": path, "mode": "100644", "type": "blob", "content": content}
                 for path, content in [("VERSION", new + "\n"), ("uv.lock", new_lock)]],
    })
    commit = api(f"repos/{repo}/git/commits", "POST", {
        "message": f"chore: release {new}", "tree": tree["sha"], "parents": [head],
    })
    if api(f"repos/{repo}/git/ref/heads/dev")["object"]["sha"] != head:
        print("dev moved while preparing the release; retry on next reconciliation")
        return
    refs = api(f"repos/{repo}/git/matching-refs/heads/{BRANCH}")
    existing = [r for r in refs if r["ref"] == f"refs/heads/{BRANCH}"]
    if existing:
        if not current:
            previous = pages(f"repos/{repo}/pulls?state=closed&head={repo.split('/')[0]}:{BRANCH}")
            if not previous or any(p["user"]["login"] != bot for p in previous):
                raise ValueError("Refusing to overwrite an unrecognized release branch")
        api(f"repos/{repo}/git/refs/heads/{BRANCH}", "PATCH", {"sha": commit["sha"], "force": True})
    else:
        api(f"repos/{repo}/git/refs", "POST", {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
    body = f"""## What
- VERSION을 `{value}`에서 `{new}`로 올리고 uv.lock을 동기화합니다.

## How To Test
- [ ] `uv sync`
- [ ] `uv build`
- [ ] `uv run k-commerce-mcp`
- [ ] Additional verification: compatibility 및 version-policy 필수 검사

## Review Focus
- patch만 1 증가하며 VERSION과 uv.lock 외의 파일은 변경하지 않습니다.
- 기존 배포 완료를 확인한 뒤 생성했습니다. CI 통과 후 봇이 병합합니다.

## Screenshots / Logs
- 이 PR의 Actions 검사 결과를 확인합니다.

## Related
- Spec / Issue / Discussion: docs/testpypi.md
"""
    if current:
        api(f"repos/{repo}/pulls/{current['number']}", "PATCH", {"title": f"chore: release {new}", "body": body})
    else:
        api(f"repos/{repo}/pulls", "POST", {"head": BRANCH, "base": "dev", "title": f"chore: release {new}", "body": body})


if __name__ == "__main__":
    main()
