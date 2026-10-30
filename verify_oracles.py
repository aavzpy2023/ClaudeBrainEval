#!/usr/bin/env python3
"""Phase 2 exit check for code tasks: the oracle must fail on the base commit, pass once the
reference solution is applied, and leave the project's full suite green.
Usage: verify_oracles.py [task_id ...]   (default: every code task)
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from envsetup import WORK
from evalcommon import ROOT, load_tasks


def sh(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kw)


def verify(task: dict) -> list[str]:
    proj = task["project"]
    test_cmd = json.loads((ROOT / "history" / f"{proj}.json").read_text()).get("test_cmd", ["python3", "-m", "unittest"])
    d = WORK / "verify" / task["id"]
    shutil.rmtree(d, ignore_errors=True)
    d.parent.mkdir(parents=True, exist_ok=True)
    sh(["git", "clone", "-q", str(ROOT / "projects" / proj), str(d)], ROOT)
    sh(["git", "checkout", "-q", task["base"]], d)
    for dest, src in task["oracle"]["files"].items():
        (d / dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / src, d / dest)
    problems = []
    if sh(task["oracle"]["cmd"], d).returncode == 0:
        problems.append("oracle PASSES on the base commit (it must fail)")
    ap = sh(["git", "apply", str(ROOT / task["oracle"]["solution"])], d)
    if ap.returncode:
        return problems + [f"solution does not apply: {ap.stderr.strip()[:200]}"]
    r = sh(task["oracle"]["cmd"], d)
    if r.returncode:
        problems.append("oracle fails with the reference solution: " + (r.stdout + r.stderr)[-300:])
    r = sh(test_cmd, d)
    if r.returncode:
        problems.append("full suite fails with the reference solution: " + (r.stdout + r.stderr)[-300:])
    return problems


def main() -> None:
    want = set(sys.argv[1:])
    bad = 0
    for t in load_tasks():
        if t["kind"] != "code" or (want and t["id"] not in want):
            continue
        problems = verify(t)
        print(("FAIL " if problems else "ok   ") + t["id"])
        for p in problems:
            print("     -", p)
        bad += bool(problems)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
