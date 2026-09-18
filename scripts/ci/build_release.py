"""Build one release, recording the exact files that must be tested and published."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def development_version(base: str, run_id: int, attempt: int) -> str:
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", base):
        raise ValueError("VERSION must contain a three-part stable version")
    if run_id < 1 or not 1 <= attempt < 1000:
        raise ValueError("run_id must be positive and attempt must be between 1 and 999")
    return f"{base}.dev{run_id * 1000 + attempt}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", action="store_true")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    version_file = root / "VERSION"
    original = version_file.read_text()
    version = original.strip()
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
