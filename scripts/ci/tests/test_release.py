import hashlib
import json
import subprocess
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from scripts.ci.build_release import development_version
from scripts.ci import build_release
from scripts.ci.fetch_testpypi import verify_download
from scripts.ci.verify_distribution import check_release


@pytest.mark.parametrize("base,published,expected", [
    ("0.1.1", [], "0.1.1"),
    ("0.1.1", ["0.1.0"], "0.1.1"),
    ("0.1.0", ["0.1.2"], "0.1.3"),
    ("0.1.0", ["0.1.9.dev42001", "0.1.10.dev43001", "0.1.2"], "0.1.11"),
    ("0.2.0", ["0.1.9.dev42001"], "0.2.0"),
    ("0.2.0", ["0.2.0.dev42001"], "0.2.1"),
    ("1.0.0", ["0.9.99"], "1.0.0"),
    ("0.1.5", ["0.1.2"], "0.1.5"),
])
def test_next_patch_version(base, published, expected):
    assert build_release.next_patch_version(base, published) == expected


@pytest.mark.parametrize("base,published", [
    ("0.1.0", ["0.2.0.dev1"]),
    ("0.9.0", ["1.0.0"]),
    ("0.1", []),
    ("0.1.0.dev1", []),
    ("0.1.0", ["0.2.0rc1"]),
])
def test_version_selection_rejects_regression_and_unsupported_versions(base, published):
    with pytest.raises(ValueError):
        build_release.next_patch_version(base, published)


def test_index_includes_empty_yanked_and_partial_releases(monkeypatch):
    payload = {"releases": {"0.1.1": [], "0.1.2.dev1": [{"yanked": True}], "0.1.3.dev1": [{"filename": "only-wheel.whl"}]}}
    monkeypatch.setattr(build_release, "urlopen", lambda *args, **kwargs: BytesIO(json.dumps(payload).encode()))
    assert build_release.next_patch_version("0.1.0", build_release.published_versions()) == "0.1.4"


@pytest.mark.parametrize("error", [URLError("offline"), HTTPError("url", 404, "missing", {}, None)])
def test_index_failure_does_not_fall_back_to_manual_version(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(build_release, "urlopen", fail)
    with pytest.raises(type(error)):
        build_release.published_versions()


def test_resolved_version_is_built_recorded_and_restored(tmp_path, monkeypatch):
    (tmp_path / "VERSION").write_text("0.1.1\n")
    output = tmp_path / "release"
    monkeypatch.setattr(build_release, "__file__", str(tmp_path / "scripts/ci/build_release.py"))
    monkeypatch.setattr("sys.argv", ["build_release.py", "--resolve-testpypi", "--development", "--run-id", "42", "--attempt", "1", "--output", str(output)])
    monkeypatch.setattr(build_release, "published_versions", lambda: ["0.1.2.dev1"])
    monkeypatch.setattr(build_release.subprocess, "check_output", lambda *args, **kwargs: "commit-sha\n")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    def build(*args, **kwargs):
        assert (tmp_path / "VERSION").read_text() == "0.1.3.dev42001\n"
        (output / "dist").mkdir()
        (output / "dist/k_commerce-0.1.3.dev42001-py3-none-any.whl").write_bytes(b"wheel")
        (output / "dist/k_commerce-0.1.3.dev42001.tar.gz").write_bytes(b"sdist")
    monkeypatch.setattr(build_release.subprocess, "run", build)
    build_release.main()
    assert json.loads((output / "release.json").read_text())["version"] == "0.1.3.dev42001"
    assert (tmp_path / "VERSION").read_text() == "0.1.1\n"


def test_development_versions_are_distinct_for_runs_and_retries():
    assert development_version("0.1.0", 42, 1) == "0.1.0.dev42001"
    assert len({development_version("0.1.0", run, attempt) for run in (42, 43) for attempt in (1, 2, 999)}) == 6


@pytest.mark.parametrize("base,run,attempt", [("0.1.0.dev1", 42, 1), ("0.1", 42, 1), ("0.1.0", 0, 1), ("0.1.0", 42, 0), ("0.1.0", 42, 1000)])
def test_development_version_rejects_ambiguous_or_invalid_inputs(base, run, attempt):
    with pytest.raises(ValueError):
        development_version(base, run, attempt)


def test_changed_distribution_cannot_pass_verification(tmp_path):
    (tmp_path / "dist").mkdir()
    files = {"k_commerce-0.1.0-py3-none-any.whl": b"wheel", "k_commerce-0.1.0.tar.gz": b"sdist"}
    manifest = {"name": "k-commerce", "version": "0.1.0", "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    (tmp_path / "release.json").write_text(json.dumps(manifest))
    for name, data in files.items():
        (tmp_path / "dist" / name).write_bytes(data)
    assert check_release(tmp_path) == manifest
    (tmp_path / "dist" / next(iter(files))).write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        check_release(tmp_path)


def test_published_file_must_match_tested_bytes():
    digest = hashlib.sha256(b"tested").hexdigest()
    verify_download(b"tested", digest)
    with pytest.raises(ValueError, match="does not match"):
        verify_download(b"different", digest)


def test_failed_build_restores_original_version(tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    version_file.write_text("0.1.0\n")
    monkeypatch.setattr(build_release, "__file__", str(tmp_path / "scripts/ci/build_release.py"))
    monkeypatch.setattr("sys.argv", ["build_release.py", "--development", "--run-id", "42", "--attempt", "1", "--output", str(tmp_path / "release")])

    def fail_build(command, **kwargs):
        assert version_file.read_text() == "0.1.0.dev42001\n"
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(build_release.subprocess, "run", fail_build)
    with pytest.raises(subprocess.CalledProcessError):
        build_release.main()
    assert version_file.read_text() == "0.1.0\n"
