---
name: staged-code-review
description: Perform a senior-engineer-level code review of the current git staged changes (git diff --staged). Trigger this whenever the user runs /staged-code-review, asks to "review my staged changes", "review before I commit", "check what I'm about to commit", or similar — even if they don't use the exact slash command. Do NOT use for reviewing a whole repo, an unstaged working tree, a PR on GitHub, or a specific file the user pastes in directly (only staged git changes).
---

# Staged Code Review

Reviews exactly what's staged for commit (`git diff --staged`) — nothing more, nothing less. The point is to catch problems *before* they land in a commit, with direct, specific, actionable feedback. No praise, no padding, no restating the diff back to the user.

## Workflow

1. **Confirm there's a repo and staged content.**
   ```bash
   git rev-parse --is-inside-work-tree
   git diff --staged --stat
   ```
   If nothing is staged, say so plainly and stop — don't review unstaged or untracked files unless the user explicitly asks you to widen scope.

2. **Gather context, not just the diff.**
   - `git diff --staged` for the actual changes.
   - `git diff --staged -U10` (or more) when a hunk needs surrounding code to judge correctness — 3-line default context is often not enough to tell if a change is safe.
   - `git log --oneline -10` for recent history / conventions in this repo.
   - If a changed function is called elsewhere, `grep`/search for call sites before flagging a signature change as safe or unsafe.
   - Read full files (not just the diff hunk) when the diff touches control flow, error handling, or shared state — a 5-line hunk can be wrong in ways only visible in the surrounding function.

3. **Review against these categories, in priority order.** Skip a category entirely in the output if there's nothing to say — don't manufacture filler.
   - **Correctness** — logic errors, off-by-one, wrong operator, unhandled edge case, race condition, incorrect assumption about input shape.
   - **Security** — injection, unsanitized input, secrets/credentials in the diff, unsafe deserialization, broken auth/access checks, path traversal.
   - **Data integrity / side effects** — migrations without rollback, destructive operations without guards, silent data loss, non-idempotent operations that need to be idempotent.
   - **Error handling** — swallowed exceptions, bare `except`, missing error propagation, failure modes left unhandled.
   - **Tests** — new logic with no corresponding test change; existing tests that should have changed but didn't; tests that only assert happy path.
   - **API / interface changes** — breaking changes to public functions, exported types, endpoint contracts, or config shape; missing version/migration considerations.
   - **Performance** — obvious algorithmic regressions (N+1 queries, unnecessary loops over large data, blocking calls in hot paths). Don't chase micro-optimizations that don't matter here.
   - **Style / maintainability** — only flag if it genuinely hurts readability or diverges from patterns already established in this repo/file. Don't nitpick formatting a linter would catch.
   - **Architectural decisions** — check whether the staged change conflicts with an existing architectural decision, ADR, architecture/design document, module boundary, dependency rule, or clearly established architectural convention in the repository. If it breaches an existing architectural decision, flag it as a finding and explain the exact conflict and concrete correction. If it represents an important change to an existing architectural decision, do not automatically treat it as a defect: explain what architectural decision is changing, why the change matters, and what existing assumptions or boundaries it affects. If appropriate, recommend updating or creating the relevant ADR/documentation. Do not invent an architectural decision when the repository provides no evidence for one.

4. **Check the diff is self-consistent.** Does it do what the (most recent) commit message, PR description, or the user's stated intent says it does? If the user hasn't stated intent, infer it from the change and flag anything that looks incomplete relative to itself (e.g., a new field added to a struct but not to its serializer).

5. **Check architectural consistency before finalizing findings.** Distinguish clearly between: **(a) architectural breach** — the change contradicts an existing documented or clearly established decision; report the conflict and required fix; **(b) important architectural change** — the change intentionally alters an existing decision or introduces a significant new architectural direction; explain the change and its implications rather than automatically calling it a bug; and **(c) no architectural evidence** — no relevant ADR, architecture documentation, or established repository pattern can be found, in which case do not speculate. Read relevant repository documentation and surrounding code only as needed to establish architectural context; keep the actual review scope limited to the staged diff.

## Output format

Lead with a one-line verdict, then findings grouped by severity. No summary paragraph restating what the diff does.

```
Verdict: [Ship it / Fix before commit / Needs rework]

🔴 Blocking
- `path/to/file.py:42` — <the actual problem, stated as fact, not a question>
  → <the fix, concretely, not "consider fixing this">

🟡 Worth addressing
- `path/to/file.py:88` — ...

🟢 Optional / nit
- ...
```

Rules for the findings themselves:
- Cite the actual file and line (or hunk) — never a vague "in the diff somewhere."
- State the problem as a fact: "this drops the exception on line 42" not "have you considered whether errors are handled here?"
- Give the fix, not just the complaint. If there are two reasonable fixes, name both in one line and say which you'd pick.
- If a hunk is genuinely fine, don't invent a nitpick to have something to say about it — silence on a file/hunk is a valid outcome.
- If you had to assume something about intent to judge a hunk (e.g. "assuming this is meant to be idempotent"), say so inline next to that finding, not in a disclaimer block at the top or bottom.

## Boundaries

- Only the staged diff is in scope. If the user's staged changes depend on unstaged changes to work, flag that as a blocker rather than silently reviewing the unstaged code too.
- Don't run the code, run tests, or modify any files unless the user explicitly asks you to fix something after the review.
- Don't restate `git diff --staged --stat` output to the user as if it were analysis — it's context-gathering, not a finding.
- If the diff is large enough that a full line-by-line review would be noise, prioritize Correctness/Security/Data-integrity findings and say explicitly what you deprioritized and why, rather than giving shallow coverage of everything.
