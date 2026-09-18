import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

import pytest

from scripts.ci import release_state as state


def record(draft=True, commit="release-sha"):
    return {"id": 7, "draft": draft, "tag_name": "testpypi-v0.1.3", "body": json.dumps({"version": "0.1.3", "commit": commit}), "assets": []}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_SHA", "latest-sha")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "outputs"))
    (tmp_path / "VERSION").write_text("0.1.3\n")
    monkeypatch.setattr(state, "version_commit", lambda: "release-sha")
    return tmp_path


@pytest.mark.parametrize("draft,revision,publish", [(True, "release-sha", "true"), (False, "latest-sha", "false")])
def test_reserve_uses_original_version_commit_only_for_pending_release(repo, monkeypatch, draft, revision, publish):
    monkeypatch.setattr(state, "record_for", lambda value: record(draft))
    state.reserve()
    result = (repo / "outputs").read_text()
    assert f"revision={revision}" in result
    assert f"publish={publish}" in result


def test_cannot_reuse_version_for_another_commit(repo, monkeypatch):
    monkeypatch.setattr(state, "record_for", lambda value: record(commit="different"))
    with pytest.raises(ValueError, match="another commit"):
        state.reserve()


def test_previous_pending_release_blocks_new_reservation(repo, monkeypatch):
    monkeypatch.setattr(state, "record_for", lambda value: None)
    monkeypatch.setattr(state, "pages", lambda path: [record()])
    with pytest.raises(ValueError, match="pending"):
        state.reserve()


def test_first_reservation_pins_commit(repo, monkeypatch):
    monkeypatch.setattr(state, "record_for", lambda value: None)
    monkeypatch.setattr(state, "pages", lambda path: [])
    calls = []
    def api(path, method, data):
        calls.append(data)
        return record()
    monkeypatch.setattr(state, "api", api)
    state.reserve()
    assert calls[0]["draft"] is True
    assert calls[0]["target_commitish"] == "release-sha"
    assert json.loads(calls[0]["body"])["commit"] == "release-sha"


def make_distribution(directory):
    (directory / "dist").mkdir(parents=True)
    files = {"k_commerce-0.1.3-py3-none-any.whl": b"wheel", "k_commerce-0.1.3.tar.gz": b"sdist"}
    for name, data in files.items():
        (directory / "dist" / name).write_bytes(data)
    manifest = {"name": "k-commerce", "version": "0.1.3", "commit": "release-sha", "files": {n: hashlib.sha256(d).hexdigest() for n, d in files.items()}}
    (directory / "release.json").write_text(json.dumps(manifest))
    return manifest


def test_retry_restores_exact_persisted_files(repo, monkeypatch):
    directory = repo / "original"
    expected = make_distribution(directory)
    saved = record()
    monkeypatch.setattr(state, "checked_record", lambda release_id: (saved, json.loads(saved['body'])))
    calls = []
    monkeypatch.setattr(state.subprocess, "run", lambda command, **kwargs: calls.append(command))
    state.persist(7, directory)
    bundle = (repo / state.ASSET).read_bytes()
    assert calls[0][:3] == ['gh', 'release', 'upload']
    saved['assets'] = [{'id': 4, 'name': state.ASSET, 'state': 'uploaded'}]
    def download(command, **kwargs):
        kwargs['stdout'].write(bundle)
    monkeypatch.setattr(state.subprocess, 'run', download)
    monkeypatch.setattr(state.subprocess, 'check_output', lambda *args, **kwargs: 'release-sha\n')
    state.restore(7, repo / 'restored')
    assert state.check_release(repo / 'restored') == expected
    assert 'restored=true' in (repo / 'outputs').read_text()


def test_persist_refuses_changed_bytes(repo, monkeypatch):
    directory = repo / "release"
    make_distribution(directory)
    saved = record()
    saved['assets'] = [{'id': 4, 'name': state.ASSET, 'state': 'uploaded'}]
    monkeypatch.setattr(state, "checked_record", lambda release_id: (saved, json.loads(saved['body'])))
    monkeypatch.setattr(state.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess([], 0, stdout=b'previous bundle'))
    with pytest.raises(ValueError, match='replace'):
        state.persist(7, directory)


def test_archive_traversal_is_rejected(repo, monkeypatch):
    saved = record()
    saved['assets'] = [{'id': 4, 'name': state.ASSET, 'state': 'uploaded'}]
    archive_path = repo / 'malicious.tar'
    with tarfile.open(archive_path, 'w') as archive:
        archive.addfile(tarfile.TarInfo('../outside'))
    payload = archive_path.read_bytes()
    monkeypatch.setattr(state, 'checked_record', lambda release_id: (saved, json.loads(saved['body'])))
    monkeypatch.setattr(state.subprocess, 'run', lambda command, **kwargs: kwargs['stdout'].write(payload))
    with pytest.raises(ValueError, match='Unsafe'):
        state.restore(7, repo / 'restored')
    assert not (repo / 'outside').exists()


def test_cannot_complete_without_saved_artifact(repo, monkeypatch):
    saved = record()
    monkeypatch.setattr(state, 'checked_record', lambda release_id: (saved, json.loads(saved['body'])))
    with pytest.raises(ValueError, match='without retained'):
        state.complete(7)
