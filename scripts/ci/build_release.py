"""Build one release, recording the exact files that must be tested and published."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

STABLE_VERSION = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    version_file = root / "VERSION"
    version = version_file.read_text().strip()
    if not re.fullmatch(STABLE_VERSION, version):
        raise ValueError("VERSION must contain a three-part stable version")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run(["uv", "build", "--no-sources", "--out-dir", str(output / "dist")], cwd=root, check=True)
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
