"""Reserve releases and retain the exact verified bytes for retries in draft releases."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

from scripts.ci.github_api import api, pages, repository
from scripts.ci.version_policy import version
from scripts.ci.verify_distribution import check_release

ASSET = "release-bundle.tar"


def record_for(value):
    matches = [r for r in pages(f"repos/{repository()}/releases") if r["tag_name"] == f"testpypi-v{value}"]
    if len(matches) > 1:
        raise ValueError("Duplicate release records")
    return matches[0] if matches else None


def record_metadata(record):
    data = json.loads(record["body"])
    version(data["version"])
    if record["tag_name"] != f"testpypi-v{data['version']}":
        raise ValueError("Release record version mismatch")
    return data


def version_commit():
    return subprocess.check_output(["git", "log", "--first-parent", "-1", "--format=%H", "--", "VERSION"], text=True).strip()


def output(**values):
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        for key, value in values.items():
            stream.write(f"{key}={value}\n")


def reserve():
    value = Path("VERSION").read_text().strip()
    version(value)
    commit = version_commit()
    record = record_for(value)
    if record:
        if record_metadata(record)["commit"] != commit:
            raise ValueError("This version is already reserved for another commit")
    else:
        pending = [r for r in pages(f"repos/{repository()}/releases") if r["draft"] and r["tag_name"].startswith("testpypi-v")]
        if pending:
            raise ValueError("Finish the pending release before reserving another version")
        record = api(f"repos/{repository()}/releases", "POST", {
            "tag_name": f"testpypi-v{value}", "target_commitish": commit,
            "name": f"TestPyPI {value}", "body": json.dumps({"version": value, "commit": commit}),
            "draft": True, "prerelease": True,
        })
    output(revision=commit if record["draft"] else os.environ["GITHUB_SHA"], publish=str(record["draft"]).lower(), release_id=record["id"])


def checked_record(release_id):
    record = api(f"repos/{repository()}/releases/{release_id}")
    return record, record_metadata(record)


def restore(release_id, destination):
    record, metadata = checked_record(release_id)
    assets = [a for a in record["assets"] if a["name"] == ASSET]
    if not assets:
        output(restored="false")
        return
    if len(assets) != 1 or assets[0]["state"] != "uploaded":
        raise ValueError("Incomplete release asset; operator recovery required")
    bundle = destination.parent / ASSET
    with bundle.open("wb") as stream:
        subprocess.run(["gh", "api", f"repos/{repository()}/releases/assets/{assets[0]['id']}",
                        "-H", "Accept: application/octet-stream"], stdout=stream, check=True)
    with tarfile.open(bundle) as archive:
        members = archive.getmembers()
        if any(not m.isfile() or m.name.startswith("/") or ".." in Path(m.name).parts for m in members):
            raise ValueError("Unsafe release archive")
        names = [m.name for m in members]
        if len(names) != 3 or "release.json" not in names or sum(n.startswith("dist/") for n in names) != 2:
            raise ValueError("Unexpected release archive contents")
        destination.mkdir(parents=True, exist_ok=False)
        archive.extractall(destination, filter="data")
    manifest = check_release(destination)
    if manifest["version"] != metadata["version"] or manifest["commit"] != metadata["commit"]:
        raise ValueError("Reserved version/commit differs from stored artifact")
    output(restored="true")


def persist(release_id, directory):
    record, metadata = checked_record(release_id)
    manifest = check_release(directory)
    if manifest["version"] != metadata["version"] or manifest["commit"] != metadata["commit"]:
        raise ValueError("Cannot persist artifacts for a different release")
    existing = [a for a in record["assets"] if a["name"] == ASSET]
    bundle = directory.parent / ASSET
    # Deterministic archive metadata enables byte comparison across retries.
    with tarfile.open(bundle, "w") as archive:
        for path in [directory / "release.json", *sorted((directory / "dist").iterdir())]:
            info = tarfile.TarInfo(path.relative_to(directory).as_posix())
            info.size = path.stat().st_size
            with path.open("rb") as stream:
                archive.addfile(info, stream)
    if existing:
        result = subprocess.run(["gh", "api", f"repos/{repository()}/releases/assets/{existing[0]['id']}",
                                 "-H", "Accept: application/octet-stream"], capture_output=True, check=True)
        if hashlib.sha256(result.stdout).digest() != hashlib.sha256(bundle.read_bytes()).digest():
            raise ValueError("Refusing to replace reserved release bytes")
    else:
        subprocess.run(["gh", "release", "upload", record["tag_name"], str(bundle), "--repo", repository()], check=True)


def complete(release_id):
    record, metadata = checked_record(release_id)
    if not any(a["name"] == ASSET and a["state"] == "uploaded" for a in record["assets"]):
        raise ValueError("Cannot complete a release without retained artifacts")
    api(f"repos/{repository()}/releases/{release_id}", "PATCH", {"draft": False, "make_latest": "false"})
    print(f"Verified release {metadata['version']} at {metadata['commit']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["reserve", "restore", "persist", "complete"])
    parser.add_argument("--release-id", type=int)
    parser.add_argument("--directory", type=Path, default=Path("release"))
    args = parser.parse_args()
    if args.command == "reserve":
        reserve()
    elif args.release_id is None:
        parser.error("--release-id is required")
    elif args.command == "restore":
        restore(args.release_id, args.directory)
    elif args.command == "persist":
        persist(args.release_id, args.directory)
    else:
        complete(args.release_id)


if __name__ == "__main__":
    main()
