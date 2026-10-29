#!/usr/bin/env python3
"""Run the pending experiment runs. Resumable: reruns only what has no status=ok row."""
import argparse

from evalcommon import done_ids, planned_runs


def execute(run: dict) -> dict:
    # Phase 1 fills this in: fresh copy of the project snapshot in an isolated HOME and brain
    # data dir, apply the condition, `claude -p --output-format stream-json --verbose`,
    # save the evidence files, return a results row.
    raise NotImplementedError("runner body arrives with the first frozen snapshot (P1)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["pilot", "main"], required=True)
    ap.add_argument("--max-runs", type=int, default=0, help="0 = no limit")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    done = done_ids()
    pending = [r for r in planned_runs(args.phase) if r["run_id"] not in done]
    print(f"{args.phase}: {len(pending)} pending, {len(done)} done")
    if args.max_runs:
        pending = pending[: args.max_runs]
    if args.dry_run:
        for r in pending[:20]:
            print(" ", r["run_id"])
        return
    for r in pending:
        execute(r)


if __name__ == "__main__":
    main()
