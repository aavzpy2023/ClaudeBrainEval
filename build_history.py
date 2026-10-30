#!/usr/bin/env python3
"""Replay a project's scripted sessions through `claude -p` so the brain archives them for real.

Resumable: progress is kept in history/<project>.state.json. Stops at the first failed session.
"""
import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from envsetup import BRAIN_REPO, WORK, make_env, reset

ROOT = Path(__file__).parent


def git(proj: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(proj), *args], capture_output=True, text=True, check=True).stdout.strip()


def tests_pass(proj: Path, test_cmd: list[str]) -> bool:
    return subprocess.run(test_cmd, cwd=proj, capture_output=True).returncode == 0


def freeze(project: str, proj: Path, db: Path) -> None:
    """Copy the finished repo and brain database into the repo's snapshot folders."""
    keep = ROOT / "projects" / project
    if not keep.exists():
        subprocess.run(["git", "clone", "-q", str(proj), str(keep)], check=True)
    snap = ROOT / "snapshots" / project
    snap.mkdir(parents=True, exist_ok=True)
    # The brain database is in WAL mode: a plain file copy misses what is still in the -wal file.
    (snap / "brain.db").unlink(missing_ok=True)
    src = sqlite3.connect(db)
    dst = sqlite3.connect(snap / "brain.db")
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--max-sessions", type=int, default=0)
    ap.add_argument("--restart", action="store_true", help="wipe the project, its brain db and progress")
    args = ap.parse_args()

    script = json.loads((ROOT / "history" / f"{args.project}.json").read_text())
    env_name = f"history-{args.project}"
    proj = WORK / env_name / args.project
    keep = ROOT / "projects" / args.project
    state_file = ROOT / "history" / f"{args.project}.state.json"

    if args.restart:
        reset(env_name)
        state_file.unlink(missing_ok=True)
        shutil.rmtree(proj, ignore_errors=True)
    if not proj.exists():
        proj.mkdir(parents=True)
        git(proj, "init", "-q", "-b", "main")
        git(proj, "-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "commit", "--allow-empty", "-qm", "init")
    state = json.loads(state_file.read_text()) if state_file.exists() else {"done": []}

    env = make_env(env_name)
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "eval"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "eval@example.invalid"
    ran = 0
    for s in script["sessions"]:
        if s["id"] in state["done"]:
            continue
        if args.max_sessions and ran >= args.max_sessions:
            break
        before = git(proj, "rev-parse", "HEAD")
        cmd = ["claude", "-p", s["prompt"], "--model", script["model"], "--effort", script["effort"],
               "--allowedTools", script.get("tools", "Read,Write,Edit,Glob,Grep,Bash(git *),Bash(python3 *),Bash(python *)")]
        r = subprocess.run(cmd, cwd=proj, env=env, capture_output=True, text=True, timeout=1200)
        after = git(proj, "rev-parse", "HEAD")
        ok = r.returncode == 0 and after != before and tests_pass(proj, script.get("test_cmd", [sys.executable, "-m", "unittest"]))
        print(f"{s['id']}: exit={r.returncode} commit={'yes' if after != before else 'NO'} tests={'ok' if ok else 'FAIL'}")
        if not ok:
            print(r.stdout[-800:], r.stderr[-400:])
            sys.exit(1)
        state["done"].append(s["id"])
        state.setdefault("commits", {})[s["id"]] = after
        state_file.write_text(json.dumps(state, indent=2))
        ran += 1

    if len(state["done"]) == len(script["sessions"]) and not state.get("digest"):
        out = subprocess.run(
            [sys.executable, "-c", f"from brain.autodigest import run; print(run({re.sub('[^a-z0-9]', '', args.project.lower())!r}))"],
            cwd=BRAIN_REPO, env={**env, "CLAUDE_BRAIN_AUTODIGEST": "", "CLAUDE_BRAIN_DIGEST_MODEL": script["model"]},
            capture_output=True, text=True)
        print("digest:", out.stdout.strip(), out.stderr[-300:])
        state["digest"] = out.stdout.strip() == "True"
        state_file.write_text(json.dumps(state, indent=2))
        freeze(args.project, proj, WORK / env_name / "brain" / "brain.db")


if __name__ == "__main__":
    main()
