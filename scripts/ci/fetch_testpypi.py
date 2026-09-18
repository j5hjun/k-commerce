"""Fetch the exact release from TestPyPI and verify it against the build manifest."""

import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import urlopen


def verify_download(data: bytes, expected: str) -> None:
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Published distribution does not match the tested artifact")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    url = f"https://test.pypi.org/pypi/{quote(manifest['name'], safe='')}/{quote(manifest['version'], safe='')}/json"
    for attempt in range(12):
        try:
            with urlopen(url, timeout=15) as response:
                metadata = json.load(response)
            remote = {item["filename"]: item for item in metadata["urls"]}
            if not manifest["files"].keys() <= remote.keys():
                raise RuntimeError("Distributions are not yet visible on TestPyPI")
            break
        except (HTTPError, URLError, TimeoutError, RuntimeError):
            if attempt == 11:
                raise
            time.sleep(5)
    output = args.output.resolve()
    (output / "dist").mkdir(parents=True, exist_ok=False)
    for filename, expected in manifest["files"].items():
        if Path(filename).name != filename:
            raise ValueError("Invalid distribution filename")
        item = remote[filename]
        parsed = urlparse(item["url"])
        if parsed.scheme != "https" or parsed.hostname != "test-files.pythonhosted.org":
            raise ValueError("Unexpected TestPyPI file host")
        if item["digests"]["sha256"] != expected:
            raise ValueError("TestPyPI metadata hash does not match the tested artifact")
        with urlopen(item["url"], timeout=30) as response:
            data = response.read()
        verify_download(data, expected)
        (output / "dist" / filename).write_bytes(data)
    (output / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified TestPyPI release {manifest['name']}=={manifest['version']}")


if __name__ == "__main__":
    main()
