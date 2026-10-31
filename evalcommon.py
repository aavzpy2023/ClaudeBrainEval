"""Shared helpers: the run matrix and the results ledger."""
import csv
import json
import os
import random
from pathlib import Path

ROOT = Path(__file__).parent
RUNS = Path(os.environ["EVAL_RUNS_DIR"]) if "EVAL_RUNS_DIR" in os.environ else ROOT / "runs"  # probes write elsewhere
RESULTS = RUNS / "results.csv"
COLUMNS = [
    "run_id", "task_id", "project", "category", "condition", "rep", "arm", "model", "effort",
    "status", "new_input", "cache_creation", "cache_read", "output", "turns", "latency_s",
    "cost_usd_est", "quality", "tests_passed", "timestamp",
]


def load_tasks() -> list[dict]:
    tasks = []
    for f in sorted((ROOT / "bench" / "tasks").glob("*.json")):
        tasks += json.loads(f.read_text())
    return tasks


def load_matrix() -> dict:
    return json.loads((ROOT / "bench" / "matrix.json").read_text())


def run_id(task_id: str, condition: str, rep: int, arm: str) -> str:
    return f"{task_id}.{condition}.r{rep}.{arm}"


def planned_runs(phase: str) -> list[dict]:
    """Every run the protocol asks for in `phase`, in a seeded random order."""
    matrix, tasks = load_matrix(), load_tasks()
    runs = []
    for arm in matrix["arms"]:
        if phase not in arm["phases"]:
            continue
        reps = matrix["pilot_reps"] if phase == "pilot" else arm["reps"]
        for task in tasks:
            if phase == "pilot" and not task.get("pilot"):
                continue
            subset = arm.get("task_subset")
            if subset and not task.get(subset):
                continue
            for cond in arm.get("conditions", matrix["conditions"]):
                for rep in range(1, reps + 1):
                    runs.append({
                        "run_id": run_id(task["id"], cond, rep, arm["name"]),
                        "task": task, "condition": cond, "rep": rep, "arm": arm,
                    })
    random.Random(matrix["seed"]).shuffle(runs)
    return runs


def done_ids(results: Path | None = None) -> set[str]:
    """Run ids with a valid (status=ok) row. quota/error rows are retried."""
    results = results or RESULTS
    if not results.exists():
        return set()
    with results.open(newline="") as f:
        return {r["run_id"] for r in csv.DictReader(f) if r["status"] == "ok"}


def append_row(row: dict) -> None:
    """Append-only: rows are never edited or removed."""
    new = not RESULTS.exists()
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerow({c: row.get(c, "") for c in COLUMNS})
