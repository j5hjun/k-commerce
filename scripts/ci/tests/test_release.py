import hashlib
import json
import subprocess

import pytest

from scripts.ci.build_release import development_version
from scripts.ci import build_release
from scripts.ci.fetch_testpypi import verify_download
from scripts.ci.verify_distribution import check_release


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
