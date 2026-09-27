# Implementation Log — <Feature name>

- **Status:** `Not started` → matches `spec.md` Status
- **Spec:** `./spec.md`
- **Plan:** `./plan.md`

> **Append-only.** Each build session adds a dated entry and never edits older ones. This is the back-tracking record: it shows what was done, what changed, and why. Newest entry goes at the bottom.

## Log

_(empty — build sessions append dated entries here.)_

---

### YYYY-MM-DD — <Short title>

**Session scope:** ... (which slice of `plan.md` this session tackled)

**What was done**

- <file/behavior changes>

**Deviations from plan & why**

- ...

**Tests run / results**

- `pytest ...` — X passed, Y failed, Z skipped

**Decisions made** (link ADR if one was written)

- ...

**Progress**

- Plan steps ticked: ...
- Acceptance criteria now true (`spec.md`): ...