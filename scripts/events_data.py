"""Load and persist the event snapshots kept on the events-data branch; run from main.

Same rules as news_data.py: no checkout code, hooks, filters or executable bits
from the data branch participate, only the allowed paths can change, and a
stale writer fails closed instead of merging or forcing an update.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

DATA_REF = "refs/heads/events-data"
JSON_PATHS = ("eventos/crawled_events.json", "eventos/national_events.json",
              "eventos/sources_status.json", "eventos/national_sources_status.json")
TEXT_PATHS = ("eventos/coverage.md",)
SNAPSHOTS = ("eventos/crawled_events.json", "eventos/national_events.json")
MAX_BYTES = 8_000_000


def git(repo, *args, payload=None, env=None, check=True):
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
         "-C", str(repo), *args], input=payload, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=check, env=env,
    ).stdout


def blobs(repo, revision):
    """{path: blob} for the allowed paths present at revision (regular files only)."""
    found = {}
    for path in JSON_PATHS + TEXT_PATHS:
        entry = git(repo, "ls-tree", "-z", revision, "--", path)
        if not entry:
            continue
        metadata, _, name = entry.rstrip(b"\0").partition(b"\t")
        fields = metadata.split()
        if len(fields) != 3 or fields[:2] != [b"100644", b"blob"] or name != path.encode():
            raise ValueError(f"events-data must keep {path} as a regular non-executable file")
        found[path] = fields[2].decode("ascii")
    return found


def validate(path, payload):
    if len(payload) > MAX_BYTES:
        raise ValueError(f"{path} is too large")
    if path in TEXT_PATHS:
        payload.decode("utf8")
        return
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a JSON object")
    if path in SNAPSHOTS and not isinstance(value.get("events"), list):
        raise ValueError(f"{path} must contain events[]")


def load(repo, workdir, state):
    base = git(repo, "rev-parse", "HEAD^{commit}").decode().strip()
    found = blobs(repo, base)
    for path, blob in found.items():
        payload = git(repo, "cat-file", "blob", blob)
        validate(path, payload)
        target = workdir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    state.write_text(json.dumps({"base": base, "blobs": found}), encoding="utf8")
    print(f"Loaded {len(found)} event files from events-data {base}")


def persist(repo, workdir, state):
    baseline = json.loads(state.read_text(encoding="utf8"))
    if not re.fullmatch(r"[0-9a-f]{40,64}", baseline["base"]):
        raise ValueError("Invalid load state")
    # Verify the saved baseline against Git, rather than trusting supplied hashes.
    if blobs(repo, baseline["base"]) != baseline["blobs"]:
        raise ValueError("Invalid baseline blobs")
    git(repo, "fetch", "--no-tags", "origin", DATA_REF)
    parent = git(repo, "rev-parse", "FETCH_HEAD^{commit}").decode().strip()
    if blobs(repo, parent) != baseline["blobs"]:
        raise ValueError("Concurrent events-data update; rerun from the latest data")
    updates = {}
    for path in JSON_PATHS + TEXT_PATHS:
        source = workdir / path
        if not source.is_file() or source.is_symlink():
            continue
        payload = source.read_bytes()
        validate(path, payload)
        blob = git(repo, "hash-object", "-w", "--stdin", payload=payload).decode().strip()
        if blob != baseline["blobs"].get(path):
            updates[path] = blob
    if not updates:
        print("Event data unchanged; no commit or push")
        return
    with tempfile.TemporaryDirectory(prefix="events-data-index-") as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"),
                   GIT_AUTHOR_NAME="events-bot", GIT_AUTHOR_EMAIL="events-bot@users.noreply.github.com",
                   GIT_COMMITTER_NAME="events-bot", GIT_COMMITTER_EMAIL="events-bot@users.noreply.github.com")
        git(repo, "read-tree", parent, env=env)
        for path, blob in updates.items():
            git(repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git(repo, "write-tree", env=env).decode().strip()
        commit = git(repo, "commit-tree", tree, "-p", parent,
                     payload=b"Rastreo de eventos actualizado\n", env=env).decode().strip()
    # A racing remote update is rejected by Git's normal fast-forward rule.
    git(repo, "push", "--porcelain", "origin", f"{commit}:{DATA_REF}")
    print(f"Persisted {', '.join(sorted(updates))} to events-data {commit}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("load", "persist"))
    parser.add_argument("--data-repo", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        {"load": load, "persist": persist}[args.operation](args.data_repo, args.workdir, args.state)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            parser.exit(1, error.stderr.decode(errors="replace"))
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
