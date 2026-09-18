"""Build one release, recording the exact files that must be tested and published."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.request import urlopen


STABLE_VERSION = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"


def next_patch_version(base: str, published: list[str]) -> str:
    """VERSION selects the series/floor; published releases consume patch numbers."""
    match = re.fullmatch(STABLE_VERSION, base)
    if not match:
        raise ValueError("VERSION must contain a three-part stable version")
    floor = tuple(map(int, match.groups()))
    releases = []
    for version in published:
        match = re.fullmatch(STABLE_VERSION + r"(?:\.dev[0-9]+)?", version)
        if not match:
            raise ValueError(f"Unsupported published version: {version}")
        releases.append(tuple(map(int, match.groups())))
    if not releases:
        return base
    latest = max(releases)
    if floor[:2] < latest[:2]:
        raise ValueError("VERSION cannot move to an older release series")
    if floor > latest:
        return base
    return f"{latest[0]}.{latest[1]}.{latest[2] + 1}"


def published_versions() -> list[str]:
    # Fail closed on HTTP/network/schema errors: never guess a deployable version.
    with urlopen("https://test.pypi.org/pypi/k-commerce/json", timeout=30) as response:
        metadata = json.load(response)
    releases = metadata["releases"]
    if not isinstance(releases, dict):
        raise ValueError("Invalid TestPyPI releases metadata")
    # Include yanked, empty and partially uploaded releases to avoid reuse.
    return list(releases)


def development_version(base: str, run_id: int, attempt: int) -> str:
    if not re.fullmatch(STABLE_VERSION, base):
        raise ValueError("VERSION must contain a three-part stable version")
    if run_id < 1 or not 1 <= attempt < 1000:
        raise ValueError("run_id must be positive and attempt must be between 1 and 999")
    return f"{base}.dev{run_id * 1000 + attempt}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", action="store_true")
    parser.add_argument("--resolve-testpypi", action="store_true", help="Automatically select the next patch from published TestPyPI releases")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    version_file = root / "VERSION"
    original = version_file.read_text()
    version = original.strip()
    if args.resolve_testpypi:
        version = next_patch_version(version, published_versions())
    if args.development:
        if args.run_id is None or args.attempt is None:
            parser.error("development builds require --run-id and --attempt")
        version = development_version(version, args.run_id, args.attempt)
    output = args.output.resolve()
    # Never mix a previous run's distributions with this release.
    output.mkdir(parents=True, exist_ok=False)
    try:
        version_file.write_text(version + "\n")
        subprocess.run(["uv", "build", "--no-sources", "--out-dir", str(output / "dist")], cwd=root, check=True)
    finally:
        version_file.write_text(original)
    distributions = sorted(p for p in (output / "dist").iterdir() if p.name.endswith((".whl", ".tar.gz")))
    if len(distributions) != 2 or sum(p.suffix == ".whl" for p in distributions) != 1:
        raise RuntimeError("Expected exactly one wheel and one sdist")
    manifest = {
        "name": "k-commerce",
        "version": version,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in distributions},
    }
    (output / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if output_file := os.environ.get("GITHUB_OUTPUT"):
        with Path(output_file).open("a") as stream:
            stream.write(f"version={version}\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
