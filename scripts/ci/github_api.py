"""Small JSON-only GitHub API adapter. Tokens are supplied through GH_TOKEN."""

import json
import os
import subprocess


def api(path, method="GET", data=None):
    command = ["gh", "api", path, "--method", method]
    if data is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def pages(path):
    result = []
    for page in range(1, 101):
        batch = api(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise RuntimeError("Pagination exceeded safety limit")


def repository():
    return os.environ["GITHUB_REPOSITORY"]
