#!/usr/bin/env python3
"""Regenerate a history's digest from a clean copy of its brain database (no previous digests),
running the digest model outside the home tree. Usage: redigest.py <project> [model]"""
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from build_history import freeze
from envsetup import BRAIN_REPO, STATE, WORK, make_env

project = sys.argv[1]
model = sys.argv[2] if len(sys.argv) > 2 else json.loads((Path(__file__).parent / "history" / f"{project}.json").read_text())["model"]
env_name = f"history-{project}"
old = next(p for p in (STATE / env_name / "brain" / "brain.db", WORK / env_name / "brain" / "brain.db") if p.exists())
new = WORK / env_name / "brain" / "brain.db"
if old != new:
    new.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old, new)
with sqlite3.connect(new) as c:
    c.execute("DELETE FROM digests")
env = {**make_env(env_name), "CLAUDE_BRAIN_AUTODIGEST": "", "CLAUDE_BRAIN_DIGEST_MODEL": model}
key = re.sub("[^a-z0-9]", "", project.lower())
out = subprocess.run([sys.executable, "-c", f"from brain.autodigest import run; print(run({key!r}))"],
                     cwd=BRAIN_REPO, env=env, capture_output=True, text=True)
print("digest:", out.stdout.strip(), out.stderr[-300:])
freeze(project, WORK / env_name / project, new)
