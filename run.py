#!/usr/bin/env python3
"""Run the pending experiment runs. Resumable: reruns only what has no status=ok row."""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from envsetup import BRAIN_REPO, WORK, make_env, reset
from evalcommon import ROOT, append_row, done_ids, planned_runs

RAW = ROOT / "runs" / "raw"
CODE_TOOLS = "Read,Write,Edit,Glob,Grep,Bash(git *),Bash(python3 *),Bash(python *),Bash(node *),Bash(go *),Bash(npm *)"
QA_TOOLS = "Read,Glob,Grep,Bash(git *)"
RECALL_TOOL = "Bash(claude-brain *)"
RUN_TIMEOUT = 900
LEAK_MARKERS = ("Global Development Rules", "skeleton.py", "Explain, plan, report in SPANISH")
QUOTA_MARKERS = ("usage limit", "rate limit", "quota", "limit reached", "overloaded")
ORACLE_EXCLUDES = (":(exclude)tests/test_oracle.py", ":(exclude)test/oracle.test.ts", ":(exclude)oracle_test.go")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True).stdout


def final_digest(db: Path) -> str:
    con = sqlite3.connect(db)
    try:
        return con.execute("SELECT content FROM digests WHERE scope='project' "
                           "ORDER BY created_at DESC, id DESC LIMIT 1").fetchone()[0]
    finally:
        con.close()


def prepare_db(snapshot_db: Path, dest: Path, condition: str) -> None:
    """Copy the frozen brain and keep only what the condition exposes to the briefing."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(snapshot_db, dest)
    con = sqlite3.connect(dest)
    if condition == "C1":  # session list only
        con.execute("DELETE FROM digests")
    elif condition == "C2":  # digest only: the briefing skips sessions with no messages
        con.execute("UPDATE sessions SET msg_count = 0")
    con.commit()
    con.close()
    (dest.parent / "context").write_text("3")


def setup_run(run: dict, rundir: Path) -> tuple[Path, dict, str]:
    """Fresh clone of the project at the task's base, plus the environment for the condition."""
    task, cond = run["task"], run["condition"]
    project = task["project"]
    snap = ROOT / "snapshots" / project
    shutil.rmtree(rundir, ignore_errors=True)
    rundir.mkdir(parents=True)
    repo = rundir / project  # folder name = project key, as in the history runs
    subprocess.run(["git", "clone", "-q", "-b", task["base"], str(snap / "repo.bundle"), str(repo)], check=True)
    git(repo, "config", "user.name", "eval")
    git(repo, "config", "user.email", "eval@example.invalid")
    brain = cond in ("C1", "C2", "C3", "C4")
    env_name = f"run-{os.getpid()}"
    reset(env_name)
    env = make_env(env_name, brain=brain, db=rundir / "brain" / "brain.db")
    if brain:
        prepare_db(snap / "brain.db", rundir / "brain" / "brain.db", cond)
    if cond == "C4":
        cfg = Path(env["CLAUDE_CONFIG_DIR"])
        shutil.copytree(BRAIN_REPO / "skills" / "recall", cfg / "skills" / "recall")
        shim = rundir / "bin"
        shim.mkdir()
        (shim / "claude-brain").write_text(f'#!/bin/sh\nexec {sys.executable} {BRAIN_REPO / "bin" / "claude-brain"} "$@"\n')
        (shim / "claude-brain").chmod(0o755)
        env["PATH"] = f"{shim}:{env['PATH']}"
    briefing = ""
    if cond == "C5":
        briefing = final_digest(snap / "brain.db")
        (repo / "CLAUDE.md").write_text(f"# Project notes\n\n{briefing}\n")
        git(repo, "add", "CLAUDE.md")
        git(repo, "commit", "-q", "-m", "Add project notes")
    elif brain:
        payload = json.dumps({"source": "startup", "cwd": str(repo), "session_id": "probe"})
        out = subprocess.run([sys.executable, str(BRAIN_REPO / "brain" / "context.py"), "--hook"],
                             input=payload, capture_output=True, text=True, env=env, cwd=repo).stdout
        briefing = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else ""
    return repo, env, briefing


def grade_tests(task: dict, repo: Path) -> tuple[str, str]:
    """Copy the hidden oracle in and run it. Returns (tests.txt content, '1'/'0'); empty for question tasks."""
    oracle = task.get("oracle")
    if not oracle:
        return "", ""
    for dest, src in oracle["files"].items():
        shutil.copy(ROOT / src, repo / dest)
    try:
        r = subprocess.run(oracle["cmd"], cwd=repo, capture_output=True, text=True, timeout=300)
        return r.stdout + r.stderr, "1" if r.returncode == 0 else "0"
    except subprocess.TimeoutExpired:
        return "oracle timed out", "0"


def parse_result(raw: str) -> dict:
    """The CLI's final `result` event carries the usage totals."""
    result = {}
    for line in raw.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            result = ev
    return result


def execute(run: dict) -> dict:
    task, cond, arm, rid = run["task"], run["condition"], run["arm"], run["run_id"]
    rundir = WORK / "runs" / rid
    evid = RAW / rid
    shutil.rmtree(evid, ignore_errors=True)
    evid.mkdir(parents=True)
    repo, env, briefing = setup_run(run, rundir)
    tools = CODE_TOOLS if task["kind"] == "code" else QA_TOOLS
    if cond == "C4":
        tools += f",{RECALL_TOOL}"
    cmd = ["claude", "-p", task["prompt"], "--model", arm["model"], "--effort", arm["effort"],
           "--output-format", "stream-json", "--verbose", "--no-session-persistence", "--allowedTools", tools]
    t0 = time.time()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        r = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True, timeout=RUN_TIMEOUT)
        stdout, stderr, code = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        stdout, stderr, code = (out.decode() if isinstance(out, bytes) else out), "timeout", -1
    latency = time.time() - t0
    res = parse_result(stdout)
    usage = res.get("usage", {})
    answer = res.get("result", "") or ""

    tests_txt, passed = "", ""
    if code == 0 and not res.get("is_error"):
        tests_txt, passed = grade_tests(task, repo)
    git(repo, "add", "-A", "-N")
    diff = git(repo, "diff", "HEAD", "--", ".", *ORACLE_EXCLUDES)

    tail = (stdout[-3000:] + stderr).lower()
    if any(m in stdout for m in LEAK_MARKERS):
        status = "leak"
    elif (code != 0 or res.get("is_error")) and any(m in tail for m in QUOTA_MARKERS):
        status = "quota"
    elif code != 0 or res.get("is_error") or not res:
        status = "error"
    else:
        status = "ok"

    zst = subprocess.run(["zstd", "-q", "-19", "-c"], input=stdout.encode(), capture_output=True).stdout
    (evid / "transcript.jsonl.zst").write_bytes(zst)
    (evid / "briefing.txt").write_text(briefing)
    (evid / "answer.txt").write_text(answer)
    (evid / "stderr.txt").write_text(stderr)
    if diff:
        (evid / "diff.patch").write_text(diff)
    if tests_txt:
        (evid / "tests.txt").write_text(tests_txt)
    snap = ROOT / "snapshots" / task["project"]
    meta = {
        "run_id": rid, "model_requested": arm["model"], "effort": arm["effort"], "condition": cond,
        "model_resolved": next(iter(res.get("modelUsage", {})), ""),
        "claude_version": subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip(),
        "brain_commit": git(BRAIN_REPO, "rev-parse", "--short", "HEAD").strip(),
        "snapshot_db_sha256": sha(snap / "brain.db"), "snapshot_bundle_sha256": sha(snap / "repo.bundle"),
        "prompt_sha256": hashlib.sha256(task["prompt"].encode()).hexdigest(), "tools": tools,
        "started": started, "exit_code": code, "status": status,
    }
    (evid / "meta.json").write_text(json.dumps(meta, indent=2))
    reset(f"run-{os.getpid()}")
    shutil.rmtree(rundir, ignore_errors=True)

    row = {
        "run_id": rid, "task_id": task["id"], "project": task["project"], "category": task["category"],
        "condition": cond, "rep": run["rep"], "arm": arm["name"], "model": arm["model"], "effort": arm["effort"],
        "status": status, "new_input": usage.get("input_tokens", ""),
        "cache_creation": usage.get("cache_creation_input_tokens", ""),
        "cache_read": usage.get("cache_read_input_tokens", ""), "output": usage.get("output_tokens", ""),
        "turns": res.get("num_turns", ""), "latency_s": round(latency, 1),
        "cost_usd_est": res.get("total_cost_usd", ""), "tests_passed": passed, "timestamp": started,
    }
    append_row(row)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["pilot", "main"], required=True)
    ap.add_argument("--max-runs", type=int, default=0, help="0 = no limit")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="", help="substring filter on run_id, e.g. 'haiku' or 'A1-taskq'")
    args = ap.parse_args()

    done = done_ids()
    pending = [r for r in planned_runs(args.phase) if r["run_id"] not in done and args.only in r["run_id"]]
    print(f"{args.phase}: {len(pending)} pending, {len(done)} done")
    if args.max_runs:
        pending = pending[: args.max_runs]
    if args.dry_run:
        for r in pending[:20]:
            print(" ", r["run_id"])
        return
    for r in pending:
        row = execute(r)
        print(f"{r['run_id']}: {row['status']} in={row['new_input']}+{row['cache_creation']}+{row['cache_read']} "
              f"out={row['output']} turns={row['turns']} {row['latency_s']}s tests={row['tests_passed']}", flush=True)
        if row["status"] in ("quota", "leak"):
            print(f"stopping: status={row['status']}")
            break


if __name__ == "__main__":
    main()
