"""Install a verified wheel or rebuild an sdist in a fresh, isolated environment."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def check_release(directory: Path) -> dict:
    manifest = json.loads((directory / "release.json").read_text())
    files = manifest["files"]
    if len(files) != 2 or sum(name.endswith(".whl") for name in files) != 1 or sum(name.endswith(".tar.gz") for name in files) != 1:
        raise ValueError("Expected exactly one wheel and one sdist")
    for name, expected in files.items():
        if Path(name).name != name:
            raise ValueError("Distribution filename must not contain a directory")
        data = (directory / "dist" / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Distribution hash mismatch: {name}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--python-version", choices=("3.11", "3.12", "3.13"), required=True)
    parser.add_argument("--format", choices=("wheel", "sdist"), required=True)
    args = parser.parse_args()
    release = args.release_dir.resolve()
    manifest = check_release(release)
    suffix = ".whl" if args.format == "wheel" else ".tar.gz"
    artifact = release / "dist" / next(name for name in manifest["files"] if name.endswith(suffix))
    with tempfile.TemporaryDirectory(prefix="k-commerce-install-") as directory:
        temp = Path(directory)
        subprocess.run(["uv", "venv", "--python", args.python_version, str(temp / "venv")], cwd=temp, check=True)
        interpreter = temp / "venv/bin/python"
        if args.format == "sdist":
            # Build the archive on this interpreter, without reusing another job's cached wheel.
            subprocess.run([
                "uv", "build", str(artifact), "--wheel", "--no-sources", "--no-cache", "--python", str(interpreter), "--out-dir", str(temp / "built"),
            ], cwd=temp, check=True)
            artifact, = (temp / "built").glob("*.whl")
        subprocess.run(["uv", "pip", "install", "--python", str(interpreter), "--default-index", "https://pypi.org/simple/", str(artifact)], cwd=temp, check=True)
        subprocess.run(["uv", "pip", "check", "--python", str(interpreter)], cwd=temp, check=True)
        probe = temp / "check_installed.py"
        shutil.copyfile(Path(__file__).with_name("check_installed.py"), probe)
        subprocess.run([
            str(interpreter), "-I", str(probe), "--version", manifest["version"], "--python-version", args.python_version,
        ], cwd=temp, check=True, timeout=90)


if __name__ == "__main__":
    main()
