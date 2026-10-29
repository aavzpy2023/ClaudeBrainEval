"""Isolated Claude Code environments, so experiments never touch the user's real config or brain."""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
BRAIN_REPO = ROOT.parent / "claude_brain"
STATE = Path.home() / ".cache" / "claude-brain-eval"
REAL_CLAUDE = Path.home() / ".claude"
# Claude Code loads `.claude/CLAUDE.md` from every ancestor of the working directory, so any
# path under the real home would inherit the user's global instructions whatever CLAUDE_CONFIG_DIR
# or HOME say. Runs therefore work outside the home tree.
WORK = Path(os.environ.get("EVAL_WORK", "/tmp/claude-brain-eval"))


def brain_hooks() -> dict:
    """Same hooks as the user's install, minus --sync: synthetic data must never reach Neon."""
    py, hook, ctx = sys.executable, str(BRAIN_REPO / "brain" / "hook.py"), str(BRAIN_REPO / "brain" / "context.py")

    def cmd(script: str, *args: str, timeout: int = 120) -> dict:
        return {"type": "command", "command": py, "args": [script, *args], "timeout": timeout}

    return {
        "Stop": [{"hooks": [cmd(hook), cmd(ctx, "--stop-hook", timeout=5)]}],
        "SessionEnd": [{"hooks": [cmd(hook)]}],
        "SessionStart": [{"hooks": [cmd(hook), cmd(ctx, "--hook", timeout=10)]}],
    }


def make_env(name: str, brain: bool = True, db: Path | None = None) -> dict:
    """Environment variables for a `claude -p` run: own config dir (credentials symlinked from the
    real login; no global CLAUDE.md), own brain database, Neon unreachable on purpose."""
    cfg = STATE / name / "cfg"
    cfg.mkdir(parents=True, exist_ok=True)
    cred = cfg / ".credentials.json"
    if not cred.exists():
        cred.symlink_to(REAL_CLAUDE / ".credentials.json")
    settings = {"hooks": brain_hooks()} if brain else {}
    (cfg / "settings.json").write_text(json.dumps(settings, indent=2))
    db = db or WORK / name / "brain" / "brain.db"  # autodigest runs `claude -p` from this folder: keep it outside the home tree
    db.parent.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "CLAUDE_CONFIG_DIR": str(cfg),
        "CLAUDE_BRAIN_DB": str(db),
        "CLAUDE_BRAIN_AUTODIGEST": "1",  # no background digests; histories get one explicit digest
        "NEON_URL": "postgresql://nobody:x@neon.invalid/none",  # overrides ~/.config/claude-brain/.env
    }


def reset(name: str) -> None:
    shutil.rmtree(STATE / name, ignore_errors=True)
