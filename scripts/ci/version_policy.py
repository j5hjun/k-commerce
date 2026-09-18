"""Evaluate PR version changes using base-branch code and API data only."""

import argparse
import base64
import copy
import os
import re
import tomllib

from scripts.ci.github_api import api, pages, repository

OWNER = "j5hjun"
CONTEXT = "version-policy"


def version(value):
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value):
        raise ValueError("VERSION must be MAJOR.MINOR.PATCH")
    return tuple(map(int, value.split(".")))


def bump_patch(value):
    major, minor, patch = version(value)
    return f"{major}.{minor}.{patch + 1}"


def file_at(repo, path, ref):
    item = api(f"repos/{repo}/contents/{path}?ref={ref}")
    if item.get("type") != "file" or item.get("encoding") != "base64":
        raise ValueError(f"Expected a regular file: {path}")
    return base64.b64decode(item["content"]).decode()


def lock_only_versions(before, after, old, new):
    """Dynamic uv workspace versions may be omitted; no dependency drift allowed."""
    left, right = tomllib.loads(before), tomllib.loads(after)
    cleaned = copy.deepcopy(right)
    old_packages = {p["name"]: p for p in left.get("package", []) if p.get("source", {}).get("editable") is not None}
    for package in cleaned.get("package", []):
        previous = old_packages.get(package["name"])
        if previous and package.get("source") == previous.get("source") and "version" in previous:
            if previous["version"] != old or package.get("version") != new:
                raise ValueError("Unexpected workspace version in uv.lock")
            package["version"] = old
    if left != cleaned:
        raise ValueError("Release bot may only synchronize workspace versions in uv.lock")


def owner_authorized(pr, reviews):
    if pr["user"]["login"] == OWNER:
        return True
    # Only the owner's latest review of this exact head can authorize it.
    owner_reviews = [r for r in reviews if r["user"]["login"] == OWNER and r["state"] != "COMMENTED"]
    if not owner_reviews:
        return False
    latest = max(owner_reviews, key=lambda r: r["id"])
    return latest["state"] == "APPROVED" and latest["commit_id"] == pr["head"]["sha"]


def validate_change(old, new, *, owner, bot, files):
    before, after = version(old), version(new)
    if after <= before:
        raise ValueError("Version must increase")
    if after[:2] == before[:2]:
        if new != bump_patch(old):
            raise ValueError("Patch must increase by exactly one")
        if not (owner or bot):
            raise ValueError("Patch changes require the release bot or owner authorization")
    else:
        if not owner:
            raise ValueError("Minor/major changes require j5hjun authorization")
        if after[2] != 0 or (after[0] != before[0] and after[1] != 0):
            raise ValueError("A new series must reset lower version components")
    if bot and not owner and not set(files) <= {"VERSION", "uv.lock"}:
        raise ValueError("Release bot may only change VERSION and uv.lock")


def evaluate(pr, bot_login):
    repo = repository()
    if pr["base"]["ref"] not in {"dev", "main"}:
        raise ValueError("Unsupported target branch")
    base = api(f"repos/{repo}/git/ref/heads/{pr['base']['ref']}")["object"]["sha"]
    head = pr["head"]["sha"]
    old = file_at(repo, "VERSION", base).strip()
    new = file_at(repo, "VERSION", head).strip()
    version(old)
    version(new)
    bot = bool(bot_login) and pr.get("user", {}).get("login") == bot_login and pr["head"]["repo"]["full_name"] == repo and pr["head"]["ref"] == "chore/release-version"
    if old == new:
        if bot:
            raise ValueError("Release bot PR must increment VERSION")
        return "VERSION unchanged"
    if pr["base"]["ref"] == "main":
        dev = api(f"repos/{repo}/git/ref/heads/dev")["object"]["sha"]
        if pr["head"]["repo"]["full_name"] != repo or pr["head"]["ref"] != "dev" or head != dev or version(new) < version(old):
            raise ValueError("main only accepts version promotion from current dev")
        return f"Promote protected dev version {new}"
    pending = [r for r in pages(f"repos/{repo}/releases") if r["draft"] and r["tag_name"].startswith("testpypi-v")]
    if pending:
        raise ValueError("Finish the pending release before changing VERSION")
    reviews = pages(f"repos/{repo}/pulls/{pr['number']}/reviews")
    files = pages(f"repos/{repo}/pulls/{pr['number']}/files")
    paths = {f["filename"] for f in files} | {f["previous_filename"] for f in files if "previous_filename" in f}
    authorized = owner_authorized(pr, reviews)
    validate_change(old, new, owner=authorized, bot=bot, files=paths)
    if bot:
        lock_only_versions(file_at(repo, "uv.lock", base), file_at(repo, "uv.lock", head), old, new)
    return f"Authorized {old} -> {new}"


def check_pr(number, bot_login, *, publish=True):
    repo = repository()
    pr = api(f"repos/{repo}/pulls/{number}")
    if pr["state"] != "open":
        return True
    try:
        message = evaluate(pr, bot_login)
        state = "success"
    except (ValueError, KeyError) as error:
        message, state = str(error), "failure"
    if publish:
        token = os.environ.get("GH_TOKEN")
        try:
            # Controller mutations use the App; policy statuses consistently use Actions.
            if os.environ.get("GH_STATUS_TOKEN"):
                os.environ["GH_TOKEN"] = os.environ["GH_STATUS_TOKEN"]
            api(f"repos/{repo}/statuses/{pr['head']['sha']}", "POST", {
                "state": state, "context": CONTEXT, "description": message[:140],
                "target_url": f"https://github.com/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
            })
        finally:
            if token is not None:
                os.environ["GH_TOKEN"] = token
            else:
                os.environ.pop("GH_TOKEN", None)
    print(f"PR #{number}: {state}: {message}")
    return state == "success"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", required=True, type=int)
    args = parser.parse_args()
    if not check_pr(args.pr, os.environ.get("RELEASE_BOT_LOGIN", "")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
