---
inclusion: always
---
## Task Execution Rules

- Complete tasks one by one. Ask the user to review after each task is completed.
- Update `tasks.md` (mark checkbox) when a task is completed.
- Each task should have a verification step to confirm completion (test, build, manual check).
- When each task is completed, amend the commit and push to Gerrit.
- `.kiro/` changes (except `.kiro/plan/`) go to the `[PC] kiro setup` commit. All other repo changes go to the task commit. If the `[PC] kiro setup` commit is not found, output error and ask the user to handle it manually.

## Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

### 5. Plan Before Large Changes

**Write a plan for non-trivial changes. Ask before assuming.**

A plan is required when a change:
- Touches 3+ files, OR
- Exceeds ~50 lines of new/modified code

For changes below this threshold, use judgment — a brief inline plan in chat is sufficient.

When a plan is needed:
- Write it in `.kiro/plan/<N>-<feature-name>/` where N is the next sequential number (e.g., `4-parallel-fetch/`). Include a `plan.md` or `tasks.md`.
- The plan should include: goal, affected files, approach, and verification steps.
- Present the plan to the user for approval before implementing.
- If anything is ambiguous or has multiple valid approaches, ask — do not decide silently.

### 6. Learning & Feedback

**Before starting any task**, read `.kiro/learnings/<agent-name>.md` if it exists. Do not skip this step.
Apply all known corrections and output style rules found there.

- After each session where the user corrects a mistake or clarifies a misunderstanding, record the correction to `.kiro/learnings/<agent-name>.md`.
- Log format (append as table row):

| date | query | wrong answer | correct answer | fix applied |
|------|-------|--------------|----------------|-------------|
