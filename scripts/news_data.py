"""Load and persist the one mutable news-data blob; execute this from main.

No checkout code, hooks, filters, staged files or executable bits from the data
branch participate. A stale writer fails closed instead of merging editorial
history or forcing an update.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HISTORY_PATH = "data/historial.json"
DATA_REF = "refs/heads/news-data"


def git(repo, *args, payload=None, env=None):
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
         "-C", str(repo), *args], input=payload, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True, env=env,
    ).stdout


def history_blob(repo, revision):
    entry = git(repo, "ls-tree", "-z", revision, "--", HISTORY_PATH)
    metadata, _, path = entry.rstrip(b"\0").partition(b"\t")
    fields = metadata.split()
    if len(fields) != 3 or fields[:2] != [b"100644", b"blob"] or path != HISTORY_PATH.encode():
        raise ValueError("news-data must contain a regular non-executable data/historial.json")
    blob = fields[2].decode("ascii")
    return blob, git(repo, "cat-file", "blob", blob)


def validate(payload):
    value = json.loads(payload)
    if not isinstance(value, dict) or not isinstance(value.get("noticias"), list):
        raise ValueError("History must be a JSON object with noticias[]")


def load(repo, history, state):
    base = git(repo, "rev-parse", "HEAD^{commit}").decode().strip()
    blob, payload = history_blob(repo, base)
    validate(payload)
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_bytes(payload)
    state.write_text(json.dumps({"base": base, "blob": blob}), encoding="utf8")
    print(f"Loaded {HISTORY_PATH} from news-data {base}")


def persist(repo, history, state):
    baseline = json.loads(state.read_text(encoding="utf8"))
    for field in ("base", "blob"):
        if not re.fullmatch(r"[0-9a-f]{40,64}", baseline[field]):
            raise ValueError("Invalid load state")
    # Verify the saved baseline against Git, rather than trusting a supplied hash.
    base_blob, _ = history_blob(repo, baseline["base"])
    if base_blob != baseline["blob"]:
        raise ValueError("Invalid baseline blob")
    payload = history.read_bytes()
    validate(payload)
    git(repo, "fetch", "--no-tags", "origin", DATA_REF)
    parent = git(repo, "rev-parse", "FETCH_HEAD^{commit}").decode().strip()
    remote_blob, _ = history_blob(repo, parent)
    if remote_blob != base_blob:
        raise ValueError("Concurrent news-data history update; regenerate from latest data")
    blob = git(repo, "hash-object", "-w", "--stdin", payload=payload).decode().strip()
    if blob == remote_blob:
        print("History unchanged; no commit or push")
        return
    # An isolated index starts from the latest remote tree. Never stage checkout
    # files: data/historial.json is the only path that this commit can change.
    with tempfile.TemporaryDirectory(prefix="news-data-index-") as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"),
                   GIT_AUTHOR_NAME="news-bot", GIT_AUTHOR_EMAIL="news-bot@users.noreply.github.com",
                   GIT_COMMITTER_NAME="news-bot", GIT_COMMITTER_EMAIL="news-bot@users.noreply.github.com")
        git(repo, "read-tree", parent, env=env)
        git(repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{HISTORY_PATH}", env=env)
        tree = git(repo, "write-tree", env=env).decode().strip()
        commit = git(repo, "commit-tree", tree, "-p", parent,
                     payload=b"Historial de noticias actualizado\n", env=env).decode().strip()
    # A racing remote update is rejected by Git's normal fast-forward rule.
    # No retry with stale content, force, bypass, or write to the code branch.
    git(repo, "push", "--porcelain", "origin", f"{commit}:{DATA_REF}")
    print(f"Persisted only {HISTORY_PATH} to news-data {commit}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("load", "persist"))
    parser.add_argument("--data-repo", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        {"load": load, "persist": persist}[args.operation](args.data_repo, args.history, args.state)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            parser.exit(1, error.stderr.decode(errors="replace"))
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
