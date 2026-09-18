import pytest

from scripts.ci import version_policy as policy


@pytest.mark.parametrize("old,new,owner,bot", [
    ("0.1.2", "0.1.3", False, True),
    ("0.1.2", "0.1.3", True, False),
    ("0.1.3", "0.2.0", True, False),
    ("0.2.0", "1.0.0", True, False),
])
def test_authorized_transitions(old, new, owner, bot):
    policy.validate_change(old, new, owner=owner, bot=bot, files={"VERSION", "uv.lock"})


@pytest.mark.parametrize("old,new,owner,bot,files", [
    ("0.1.2", "0.1.3", False, False, {"VERSION"}),
    ("0.1.2", "0.1.4", True, False, {"VERSION"}),
    ("0.1.2", "0.2.0", False, True, {"VERSION"}),
    ("0.1.2", "0.1.2", True, False, {"VERSION"}),
    ("0.2.0", "0.1.9", True, False, {"VERSION"}),
    ("0.1.2", "0.2.1", True, False, {"VERSION"}),
    ("0.1.2", "1.1.0", True, False, {"VERSION"}),
    ("0.1.2", "0.1.3", False, True, {"VERSION", ".github/workflows/testpypi.yml"}),
    ("0.1.2", "0.1.3.dev1", True, False, {"VERSION"}),
])
def test_disallowed_transitions(old, new, owner, bot, files):
    with pytest.raises(ValueError):
        policy.validate_change(old, new, owner=owner, bot=bot, files=files)


def test_owner_review_must_match_current_head_and_not_be_revoked():
    pr = {"user": {"login": "contributor"}, "head": {"sha": "new"}}
    review = {"id": 1, "user": {"login": "j5hjun"}, "state": "APPROVED", "commit_id": "old"}
    assert not policy.owner_authorized(pr, [review])
    review["commit_id"] = "new"
    assert policy.owner_authorized(pr, [review])
    assert not policy.owner_authorized(pr, [review, {**review, "id": 2, "state": "DISMISSED"}])
    assert not policy.owner_authorized(pr, [review, {**review, "id": 2, "state": "CHANGES_REQUESTED"}])


def test_lock_only_accepts_workspace_version_changes():
    old = '[[package]]\nname = "k-commerce"\nversion = "0.1.2"\nsource = {editable = "."}\n'
    policy.lock_only_versions(old, old.replace('0.1.2', '0.1.3'), '0.1.2', '0.1.3')
    with pytest.raises(ValueError):
        policy.lock_only_versions(old, old.replace('0.1.2', '0.1.3') + 'dependencies = [{name="evil"}]\n', '0.1.2', '0.1.3')
    dynamic = '[[package]]\nname = "k-commerce"\nsource = {editable = "."}\n'
    policy.lock_only_versions(dynamic, dynamic, '0.1.2', '0.1.3')


def test_pending_release_blocks_owner_version_change(monkeypatch):
    pr = {"number": 7, "base": {"ref": "dev"}, "head": {"sha": "new"}}
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(policy, "api", lambda path: {"object": {"sha": "base"}})
    monkeypatch.setattr(policy, "file_at", lambda repo, path, ref: "0.1.2" if ref == "base" else "0.2.0")
    monkeypatch.setattr(policy, "pages", lambda path: [{"draft": True, "tag_name": "testpypi-v0.1.2"}])
    with pytest.raises(ValueError, match="pending"):
        policy.evaluate(pr, "release[bot]")


def test_main_promotion_allows_multiple_patches_from_protected_dev(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    pr = {"number": 7, "base": {"ref": "main"}, "head": {"sha": "dev-head", "ref": "dev", "repo": {"full_name": "owner/repo"}}}
    monkeypatch.setattr(policy, "api", lambda path: {"object": {"sha": "dev-head" if path.endswith('/dev') else 'main-head'}})
    monkeypatch.setattr(policy, "file_at", lambda repo, path, ref: "0.1.0" if ref == "main-head" else "0.1.5")
    assert "Promote" in policy.evaluate(pr, "release[bot]")


def test_status_failure_is_reported_on_current_head(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv("GH_TOKEN", "app-placeholder")
    monkeypatch.setenv("GH_STATUS_TOKEN", "actions-placeholder")
    calls = []
    def api(path, method="GET", data=None):
        if method == "GET":
            return {"state": "open", "head": {"sha": "head"}}
        calls.append((path, data))
    monkeypatch.setattr(policy, "api", api)
    monkeypatch.setattr(policy, "evaluate", lambda *args: (_ for _ in ()).throw(ValueError("denied")))
    assert not policy.check_pr(7, "release[bot]")
    assert calls[0][0].endswith('/statuses/head')
    assert calls[0][1]["state"] == "failure"
    assert policy.os.environ['GH_TOKEN'] == 'app-placeholder'


def test_bot_cannot_merge_non_version_work_under_release_pr_identity(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    pr = {"number": 7, "user": {"login": "release[bot]"}, "base": {"ref": "dev"},
          "head": {"sha": "head", "ref": "chore/release-version", "repo": {"full_name": "owner/repo"}}}
    monkeypatch.setattr(policy, "api", lambda path: {"object": {"sha": "base"}})
    monkeypatch.setattr(policy, "file_at", lambda *args: "0.1.3")
    with pytest.raises(ValueError, match="must increment"):
        policy.evaluate(pr, "release[bot]")
