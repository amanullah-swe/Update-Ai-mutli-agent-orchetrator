# Spec-Driven Development — how we build with Claude Code

This project is built **feature by feature, spec first**: every feature is specified before code is written, then planned, then implemented and logged. Each feature folder stores three documents so any state in the project can be back-tracked. This file defines the folder structure and the workflow.

## Folder structure

```text
specs/
├── README.md                      # this file — the workflow
├── templates/
│   ├── feature-spec.md            # WHAT — the feature's contract (interfaces, behavior, acceptance criteria)
│   ├── plan.md                    # HOW — steps, files, and test strategy, written before coding
│   ├── implementation.md          # LOG — append-only back-tracking record of what was done
│   └── decision.md                # ADR template for resolving build decisions
├── features/
│   └── <NNN>-<feature-slug>/
│       ├── spec.md                # WHAT — status: Draft → Specified → Planned → Implemented → Tested → Accepted
│       ├── plan.md                # HOW — written after the spec is Specified, before any code
│       └── implementation.md      # LOG — every build session appends a dated entry (back-tracking)
└── decisions/
    └── <NNN>-<decision-slug>.md   # resolution records (ADRs)
```

Each feature folder holds three documents:

- **`spec.md`** — *what* we're building: interfaces, behavioral contract, config, acceptance criteria. The feature's `Status:` lives here.
- **`plan.md`** — *how* we'll build it: concrete, ordered steps Claude Code can execute and tick off. Written the moment a spec becomes `Specified`.
- **`implementation.md`** — *what actually happened*: an append-only, dated log of files touched, deviations from the plan, test results, and decisions. This is the back-tracking trail.

## Lifecycle

| State        | Meaning                                                                        |
| ------------ | ------------------------------------------------------------------------------ |
| `Draft`      | Idea captured; not ready                                                        |
| `Specified`  | `spec.md` complete — interfaces, behavior, acceptance criteria                  |
| `Planned`    | `plan.md` written (steps + files + tests); ready to build                       |
| `Implemented`| Code exists behind the common interfaces; actions logged in `implementation.md` |
| `Tested`     | Unit + integration/regression tests pass for this feature                       |
| `Accepted`   | Reviewed against the acceptance checklist; merged; docs updated                 |

## Rules of the road

1. **No code before `Planned`.** A feature must be `Specified` (`spec.md`) and `Planned` (`plan.md`) before behavior is implemented. Folder scaffolding is fine.
2. **Spec-first on change.** A behavior change touches the spec first, then the plan, then the code.
3. **Feature = working unit.** Implement, test, and commit one feature (or a coherent slice) at a time.
4. **The Core Architectural Rule always applies.** New implementations plug into the common interfaces: new file → register → name in config. No `if <strategy>:` in core code.
5. **`implementation.md` is append-only.** Never rewrite history — add a new dated entry. That is how we back-track.
6. **CLAUDE.md is the contract.** Feature specs derive from CLAUDE.md (and the verbatim spec-backup). If a spec would contradict CLAUDE.md, stop and reconcile.
7. **Decisions get recorded.** Resolving an open "Build decision" produces an ADR under `specs/decisions/`.

## Working rhythm with Claude Code

1. Pick the next feature → ensure its spec is `Specified`.
2. **Plan:** ask *"plan feature <NNN>-<slug>"* → Claude Code reads `spec.md` and writes `plan.md`, moving status to `Planned`.
3. **Build:** ask *"build feature <NNN>-<slug>"* → Claude Code executes `plan.md`, ticks its steps and the spec's acceptance criteria, appends to `implementation.md`, and moves status `Implemented` → `Tested`.
4. **Review:** you check the log and checklist; on acceptance, status becomes `Accepted` and the feature is committed.

## Source of truth

- `CLAUDE.md` — condensed, authoritative product requirements + build decisions.
- `CLAUDE.md.spec-backup-2026-09-27.md` — the original spec, verbatim; final authority if CLAUDE.md and it disagree.
- `specs/` — the working specs, plans, and logs that drive each feature's build.