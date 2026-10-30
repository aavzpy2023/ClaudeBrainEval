#!/usr/bin/env python3
"""Build the incremental digest chain of a history: one digest after sessions 3, 6 and 8, each built
from the previous one plus only the activity since, exactly as the brain's auto-digest does in use.

Works on scratch copies of the brain database with the later messages removed, so the brain's own
digest code runs unmodified. The one-shot digest it replaces is kept in snapshots/<p>/digest-oneshot.txt.
Usage: chain.py <project> [n1,n2,...]
"""
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from build_history import freeze
from envsetup import BRAIN_REPO, WORK, make_env

ROOT = Path(__file__).parent
COLS = "scope, key, covers_until_ts, content, created_at, origin"


def backup(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.unlink(missing_ok=True)
    s, d = sqlite3.connect(src), sqlite3.connect(dst)
    with d:
        s.backup(d)
    s.close()
    d.close()


def main() -> None:
    project = sys.argv[1]
    checkpoints = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [3, 6, 8]
    script = json.loads((ROOT / "history" / f"{project}.json").read_text())
    env_name, key = f"history-{project}", re.sub("[^a-z0-9]", "", project.lower())
    full = WORK / env_name / "brain" / "brain.db"
    scratch_dir = WORK / env_name / "chain"

    c = sqlite3.connect(full)
    sessions = c.execute("SELECT session_id, MAX(ts) FROM messages GROUP BY session_id ORDER BY MIN(ts)").fetchall()
    oneshot = c.execute("SELECT content FROM digests WHERE key=? ORDER BY id DESC LIMIT 1", (key,)).fetchone()
    c.close()
    assert len(sessions) >= max(checkpoints), f"only {len(sessions)} sessions archived"
    snap = ROOT / "snapshots" / project
    snap.mkdir(parents=True, exist_ok=True)
    if oneshot and not (snap / "digest-oneshot.txt").exists():
        (snap / "digest-oneshot.txt").write_text(oneshot[0])

    chain: list[tuple] = []
    for n in checkpoints:
        boundary = max(ts for _, ts in sessions[:n])
        db = scratch_dir / f"step{n}.db"
        backup(full, db)
        with sqlite3.connect(db) as cx:
            cx.execute("DELETE FROM digests")
            cx.executemany(f"INSERT INTO digests ({COLS}) VALUES (?,?,?,?,?,?)", chain)
            cx.execute("DELETE FROM messages WHERE ts > ?", (boundary,))
        env = {**make_env(env_name), "CLAUDE_BRAIN_DB": str(db), "CLAUDE_BRAIN_AUTODIGEST": "",
               "CLAUDE_BRAIN_DIGEST_MODEL": script["model"]}
        out = subprocess.run([sys.executable, "-c", f"from brain.autodigest import run; print(run({key!r}))"],
                             cwd=BRAIN_REPO, env=env, capture_output=True, text=True)
        with sqlite3.connect(db) as cx:
            rows = cx.execute(f"SELECT {COLS} FROM digests WHERE key=? ORDER BY id", (key,)).fetchall()
        assert len(rows) == len(chain) + 1, f"step {n}: no new digest ({out.stdout.strip()} {out.stderr[-200:]})"
        chain.append(rows[-1])
        print(f"{project}: digest after session {n} ({len(rows[-1][3])} chars)")

    with sqlite3.connect(full) as cx:
        cx.execute("DELETE FROM digests")
        cx.executemany(f"INSERT INTO digests ({COLS}) VALUES (?,?,?,?,?,?)", chain)
    freeze(project, WORK / env_name / project, full)


if __name__ == "__main__":
    main()
