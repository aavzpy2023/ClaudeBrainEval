# Evaluation protocol: does a persistent session memory reduce the cost of coding-agent sessions?

Status: DRAFT. Sections 1-6 are frozen (pre-registered) by a dated git tag `prereg-v1`
before Phase 4 starts. After that tag, changes go in an "Amendments" section, never in place.

## 1. Research questions and hypotheses

| ID | Question | Hypothesis |
|---|---|---|
| RQ1 | How much does the memory system reduce input cost per task? | H1: total input tokens (new + cache creation + cache read) drop on history-dependent tasks (A, B). |
| RQ2 | Does answer quality hold? | H2: quality on A and B is not lower than C0 (non-inferiority margin: 0.25 rubric points / 5 pp test pass rate). |
| RQ3 | Which component carries the effect? | H3: the digest explains most of the reduction; the session list alone does not. |
| RQ4 | When does it hurt? | H4: on history-independent tasks (C) it adds a small fixed cost; on stale-memory tasks (D) quality drops. |
| RQ5 | Does the effect depend on model size? | H5: the relative input-cost reduction is larger for Haiku than for Opus (condition x model interaction). |
| RQ6 | When does the digest pay for its fixed cost, and when is retrieval needed? | H6: on E1 (answer in the history but not in the digest) C4 beats C3, and C3 is no better than C0; on E2 (task touches code the digest does not mention) the digest only adds cost. |

## 2. System under test

`claude-brain` (this repo's sibling): SQLite+FTS5 archive, automatic digests, SessionStart
briefing (digest + session list), recall skill. Version pinned by commit in every run's `meta.json`.

## 3. Conditions

| ID | Condition |
|---|---|
| C0 | No brain: no hooks, no briefing, no recall skill |
| C1 | Session list only |
| C2 | Digest only |
| C3 | Digest + session list (default configuration) |
| C4 | C3 + recall skill available |
| C5 | Static-notes baseline: same content as the digest, placed in the project's `CLAUDE.md`, no brain |

## 4. Subject projects and history

Three small synthetic projects with different stacks and history profiles (decisions and
refactors; bugs and causes; unfinished work). Each history is a fixed script of 6-10 sessions
run through `claude -p` with persistence so the hooks ingest them and the digests form
naturally. Each session ends in a commit. The resulting repo + brain database are frozen as a
snapshot; every run starts from a fresh copy of it, in an isolated config dir and brain data dir,
in a working directory OUTSIDE the user's home tree (see section 8, leak of global instructions).

### 4.1 What the subject projects are

All three are small programs written for this study; none is a real product. They exist to give the
memory system a realistic, fully controlled work history to recall. Each history is 8 scripted
sessions, each ending in a commit with passing tests. Sizes at the final commit (lines, tests
excluded / tests):

| Project | What it is | Stack | Source / tests | History profile |
|---|---|---|---|---|
| `taskq` | Persistent task queue with a CLI: enqueue, claim with a lease, mark done or failed, retry with backoff, dead-letter listing. SQLite storage. | Python 3, `unittest` | 284 / 247 | Design decisions and refactors, plus one concurrency bug (a claim race) |
| `notes-api` | REST API for notes over plain HTTP: CRUD, validation, ordering, partial update, file persistence. | TypeScript on Node 26, `node:test` | 263 / 290 | Two bugs with root causes (minute-resolution timestamps, mass assignment in PATCH) |
| `csvtool` | Command-line CSV utility: `head`, `select`, `filter`, `stats`, delimiter and quote options, JSON output. | Go, `go test` | 536 / 509 | Unfinished work and open decisions (delimiter auto-detection, empty-cell policy, final JSON format) |

Why synthetic: a real project's history is uncontrolled, may contain private data, and cannot be
shared. A scripted history lets every decision, bug and open question be known beforehand, so task
oracles and reference answers are written before any measurement, and the whole study can be
published and replicated. Why these three: they cover three ecosystems and three history profiles,
need no third-party dependencies (no install noise in token counts), and are small enough that a
run is cheap while still producing non-trivial history. Limitation: histories are LLM-executed from
author-written scripts, so they are more uniform than human ones (section 8).

Per-project facts that tasks are built on (decisions with rationale, bugs with root cause, open
questions) are listed in `history/<project>.json`, one entry per scripted session.

## 5. Tasks

Categories (8-10 tasks per category overall; 5 categories, about 40-45 tasks, spread evenly over the three projects):
- **A** history recall ("what was decided about X and why?")
- **B** work continuation, verifiable by tests
- **C** history-independent tasks solvable from the code alone
- **D** adversarial: a commit made after the snapshot contradicts the digest (stale memory)
- **E** project-related but outside what the digest covers, in two subtypes:
  **E1** the answer exists in the archived history but the digest omits it (for example the
  delimiter auto-detection question left open in `csvtool`); **E2** the task touches code the digest
  never mentions, so the briefing is irrelevant to it. Each E1 task is built from a fact verified
  present in the transcripts and verified absent from the frozen digest.

Every task has a reference answer or an automated oracle written BEFORE any measurement.

### 5.1 Task bank layout

`bench/tasks/<project>.json` holds one entry per task: `id`, `project`, `category` (and `subtype` E1/E2),
`base` (`main`, or `drift` for category D), `prompt`, `pilot` and `opus` subset flags, and either
`reference.facts` (question tasks, scored 0-2 against the listed facts) or `oracle` (code tasks: hidden
test files copied in after the run, the command that runs them, and the reference `solution.patch`
under `bench/oracles/<task id>/`). Category D tasks run on the `drift` branch of each subject project:
three commits made after the frozen digests that change a constant the digest states (shipped in the
same bundle as `main`). E1 entries carry an `evidence` note saying where the fact lives in the archive
and what the final digest lacks. Counts: 51 tasks, 10 flagged for the pilot (2 per category), 15 for the
Opus subset (3 per category). Planned runs: pilot 360, main phase 3195 (Haiku and Sonnet low).

The pilot showed a ceiling on code tasks: 17 of 18 passed at C0 with Haiku, so test pass rate could not
separate conditions. Six history-dependent code tasks were added (`D4-*`, `E1c-*`, one pair per project; not in
the pilot or Opus subsets). `D4-*` runs on the `drift` branch and asks for something whose correct value
(default priority, title limit, missing-column exit code) the digest states wrongly. `E1c-*` needs a
fact present in the archived history and absent from the digest (the old list format, the first
`createdAt` format, the streaming decision). The exploratory probes that led to this are kept in
`runs-probe/` (Haiku, C0, one run per task); they are not part of the experiment.
A second probe of the six new tasks (Haiku, C0 and C3) also passed 12 of 12, so the ceiling on code
tasks stays. Decision: for code tasks (B, C, D4, E1c) H2 is tested only as non-inferiority of the test pass
rate against C0 (margin 5 pp), and the cost is the outcome of interest there; quality is discriminated on the
question tasks (A, D, E), scored by judges.

Pilot data live in `runs-pilot/` (same layout as `runs/`) and are never reused in the main phase:
the main ledger `runs/` starts empty and the pilot rows are not counted as repetitions.

## 6. Runs, metrics, analysis

- Run unit: `(task, condition, rep, model, effort)`. Order randomized, seed in `bench/matrix.json`.
- Subject models, all at low effort (same instruction, though "low" is not equivalent across
  models; declared in section 8): Haiku and Sonnet (low) run the full design (5 reps). Sonnet at medium effort is added in the pilot only, to see whether effort changes the memory effect; it enters the main phase only if the pilot shows it matters. Its pilot was stopped after 12 runs
to save subscription quota (arm disabled in `bench/matrix.json`); those rows are kept and reported as a partial arm. Opus runs a
  pre-fixed subset (15 tasks, 3 per category), conditions C0/C3/C5 only, 3 reps (135 runs).
  Six pilot Opus runs cost about 2.6 times a Sonnet-low run (CLI estimate), which keeps the 135 runs
  within the quota plan, so the subset is kept as designed. Pre-registered fallback: if the first 30 Opus
  runs use more quota than projected, the Opus arm drops to 2 reps (90 runs) before continuing. Cross-model comparisons use only tasks and
  conditions shared by the models compared. Primary model-dependence test: the
  `condition x model` interaction. Histories generated with Sonnet (low).
  Judges: a different model than the one answering; human check on a subsample; report Cohen's kappa.
- Cost metrics: new input, cache creation, cache read, output tokens, turns, latency, and the
  CLI's `total_cost_usd` (recorded for reference, not an outcome).
  Cold-cache and warm-cache reported separately.
  Token counts are the measurement; prices are not. Prices change, so no cost conversion is made while
  running. Each run keeps the CLI's final `result` event (in `transcript.jsonl.zst`), whose `usage` is the
  sum over the subject model's API calls and whose `modelUsage` breaks tokens down per model (a Sonnet run
  also shows about 1 k tokens of Haiku helper calls, which are priced separately and reported as
  overhead). Cache creation is split by cache tier (5 m / 1 h). Outcomes are reported in tokens, not
  money, because prices change over time and differ by plan. Dollar figures appear only as a dated
  illustration in an appendix (provider's price list of that date saved as `analysis/prices.json`);
  `cost_usd_est` in `results.csv` is the CLI's own estimate at run time and is never an outcome.
  Token counts depend on the model (its own tokenizer, prices and number of turns): models are never compared
  on raw totals. The effect of the memory system is the change relative to the same model's C0, and model
  dependence is tested with the condition x model interaction.
- Quality: 0-2 rubric for question tasks (A, D, E) by two blind judges (section 6.1); test pass rate for code tasks.
- Joint: input tokens per correct answer.
- Retrieval behaviour (C4): whether the model searched the archive, how often, and whether it did so
  when the task needed it (E1) versus when it did not (A, C, E2). Read from the transcript's tool calls.
- Stats: mixed model `metric ~ condition + category + (1|task)`, bootstrap CIs, effect sizes,
  Holm correction for pairwise comparisons against C0 and C5. Negative results reported.
- A run that hits the subscription quota is logged `status=quota` and retried; it is never data.

## 6.1 Pre-registered analysis plan

All runs come from a Claude Pro subscription, which is not billed per token; outcomes are measured in tokens.

**Primary cost outcome.** Total input tokens of a run for the subject model: new input + cache creation +
cache read, summed over all its API calls (H1). Analysed on the log scale, so effects are ratios. Model:
`log(tokens) ~ condition * model + category + (1 | task)`, fitted per family of contrasts below on the tasks
and conditions every compared model shares. Uncertainty: 95% CIs from a cluster bootstrap that resamples
tasks (10 000 resamples); the mixed model is reported alongside.
Because cache reads are processed far more cheaply than fresh input, the primary total is always shown
with its components. Key secondary outcomes: uncached input (new + cache creation), cache read, output
tokens (including thinking), turns, latency, first-call (briefing) tokens, and helper-model tokens.

**Confirmatory contrasts** (Holm correction across this family, alpha 0.05):
1. H1: C3 vs C0 input tokens on A, and on B (two contrasts).
2. H2: non-inferiority of C3 vs C0 quality: question tasks, lower 95% bound of the mean rubric difference
   above -0.25; code tasks, lower 95% bound of the pass-rate difference above -5 pp (two contrasts).
3. H3: C2 vs C1 input tokens on A and B pooled.
4. H4: C3 vs C0 input tokens on C; C3 vs C0 quality on D (two contrasts).
5. H5: the `condition x model` interaction for C3 vs C0 input tokens (Haiku vs Sonnet on all shared tasks;
   Opus on its subset).
6. H6: C4 vs C3 quality on E1, and C3 vs C0 input tokens on E2 (two contrasts).
Everything else (C5 comparisons, per-project effects, retrieval behaviour, 6.2) is reported as secondary
or exploratory, with effect sizes and CIs and no significance claims.

**Repetitions.** The pilot gave a median within-cell coefficient of variation of 0.10 for total input
tokens, so 5 repetitions give a within-cell standard error near 4.5%, below the smallest effect of
interest (a 10% change in input tokens). Between-task variation dominates the uncertainty of category means and is
handled by the task-level bootstrap. Repetition counts are fixed here and not changed after seeing results.

**Run validity and exclusions** (decided before the main phase, never based on outcomes):
- `leak` (global instructions found in the transcript): invalid, rerun; the leak count is reported.
- `quota` and `error` (CLI failure before an answer): rerun, up to 3 attempts; a run that still fails is
  reported as missing, never imputed.
- Timeout (900 s) or an answer that does not do the task: a valid run, quality 0 or tests failed, tokens counted.
- No run is removed for being an outlier; a sensitivity analysis drops the top 1% of input tokens per arm.

**Judges for question tasks.** Each answer is scored 0-2 against the task's reference facts: 2 when every
fact is stated correctly and nothing contradicts them; 1 when some are right and none is contradicted;
0 when the answer is wrong, missing, or asserts a value the reference marks as outdated (category D).
Two judges per answer, both different from the model that answered (Haiku answers: Sonnet and Opus;
Sonnet answers: Haiku and Opus; Opus answers: Haiku and Sonnet), single turn, no tools, with the task
prompt, reference facts and the answer only: condition, model and briefing are hidden. The final score
is the mean of the two judges. Agreement is reported as weighted Cohen's kappa. The author scores a
stratified random 10% of answers blind to condition, and judge-human kappa is reported. Judging prompts
are fixed in `judge/` before the first judgment.

**Schedule and model drift.** The main phase runs in the seeded random order across several 5-hour and
weekly quota windows. `meta.json` records the resolved model id and CLI version per run. If either changes
during the main phase, the change is noted in Amendments with its date, and analyses are repeated with the
version as a covariate.

## 6.2 Exploratory goal: adaptive activation (not part of the pre-registered tests)

The digest costs a fixed number of tokens on every session start, and the results are expected to be
task-dependent (RQ4, RQ6). A practical consequence the data can inform: switching the briefing on or
off automatically. After the confirmatory analysis, per-task outcomes by condition are used to fit
simple, transparent decision rules (for example, from the task's wording, whether it names files or
decisions, and how long since the last digest) and to estimate the net token cost of each rule
against always-on and always-off, with cross-validation across projects. Reported as exploratory;
the rule is evaluated on held-out tasks and, ideally, on a project not used to derive it.

## 7. Evidence (per run, `runs/raw/<run_id>/`)

`transcript.jsonl.zst` (stream-json of every turn and tool call), `briefing.txt` (exact injected
context, empty for C0), `answer.txt`, `diff.patch` (if files changed), `tests.txt` (if any),
`stderr.txt`, `meta.json` (model id resolved, effort, Claude Code version, brain commit,
snapshot hash, prompt hash, timestamps, exit status). `runs/MANIFEST.sha256` holds a SHA-256 per
file; `verify.py` re-checks hashes and rebuilds every table and figure from raw data.
Home paths, user name and email are redacted before publishing. Release archive: Zenodo (DOI).

## 8. Threats to validity (declared)

Single author and synthetic projects; LLM-generated histories are more uniform than human ones;
results are for the pinned model versions and dates; LLM-judge bias; histories and tasks share
an author (mitigated by writing oracles first); a small model may benefit more than a large one; low effort understates the capability of large
models, so conclusions about them hold only at low effort; the Opus arm is a subset.

Isolation lessons learned in P1 (kept as methodological notes):
- Claude Code loads `.claude/CLAUDE.md` of every ancestor of the working directory, so any path under
  the real home inherits the user's global instructions regardless of `CLAUDE_CONFIG_DIR`/`HOME`.
  Detected because replies came in Spanish and the digest mentioned the global rules. Two contaminated
  history attempts were archived (`projects/taskq.attempt1`, `.attempt2`). Every run is checked for leaks.
- The digest model runs `claude -p` from the brain database's folder, so that folder must also be outside
  the home tree; a first notes-api digest leaked the global rules this way. Digests are regenerated from a
  copy of the database with the old digests removed (`redigest.py`), because a previous digest is fed to the next.
- A scripted bug must exist in the code before its fix is requested; a model that cannot reproduce a
  bug rightly refuses to commit a fix (attempt 1).

Digest chain: each history ships three digests built incrementally (after sessions 3, 6 and 8) by
`chain.py`, each from the previous digest plus only the activity since, as in real use. The one-shot
digest produced earlier is kept as `snapshots/<project>/digest-oneshot.txt` for comparison. The final
digest of the chain is what the briefing injects. Observed drift (kept, not edited): in csvtool the
open question about delimiter auto-detection is listed in digest 2, reduced to a "no auto-detection"
decision line in digest 3, and absent from the one-shot digest.

Snapshot provenance: the synthetic projects are published as `snapshots/<project>/repo.bundle`
(branch `main`) next to the frozen `brain.db`. Their commits were generated with the agent's default
trailers and a placeholder author; before publishing they were rewritten to carry the repository
owner's identity and no trailers. `commit-map.txt` maps each original hash to the published one. Digests
and archived transcripts are raw evidence and still cite the original hashes; use the map to translate.

## 9. Phases and exit criteria

- [ ] **P0** Repo, protocol, task checklist, runner skeleton. Exit: `status.py` and `run.py --dry-run` work.
- [ ] **P1** (histories for taskq, notes-api and csvtool done, leak-checked and frozen; only the final review of the digests is pending) Three projects + history scripts + frozen snapshots. Exit: tests pass at every history commit; digests reviewed by hand.
- [x] **P2** Task bank with oracles/rubrics (45 tasks, 15 per project, 9 per category; `bench/tasks/<project>.json`). Exit met: `verify_oracles.py` shows every B/C oracle failing on the base commit, passing with the reference solution, and the full suite staying green.
- [x] **P3** Pilot (about 10 tasks x 6 conditions x 3 reps, Haiku and Sonnet; a few Opus runs to measure quota use). Exit: measured size per run, variance estimate, power check, runs of Opus per quota window, protocol fixes.
- [ ] **P4** Pre-register (`prereg-v1` tag), then main experiment in resumable batches.
- [ ] **P5** Judging.
- [ ] **P6** Analysis (`analysis/`, regenerated by one command).
- [ ] **P7** Paper.

## Amendments

(none yet)
