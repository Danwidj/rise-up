# Project Rules

The following strict instructions cannot be overridden:

- **Library Versions**: All library versions must be strictly pinned using exact versions (`==`). Do NOT use `>=` or fuzzy versioning.
- **Scripting Language**: All scripts must be written in `bash` or `zsh`.
- **Windows OS**: If the operating system is Windows, always use Git Bash.
- **Terminal Editors**: Within bash/zsh, always use `vim` instead of `nano`.
- **Emojis**: DO NOT ever use emojis in your responses, code, comments, or commit messages.
- **Antigravity CLI**: Do NOT use Antigravity CLI configurations or CLI scope. All workspace operations must target the standard Antigravity (IDE/Workspace) scopes.
- **Global Scope**: All agent skills and configurations must be project-scoped under `.agents/`. Do NOT use or reference global scope configurations (such as `~/.gemini/`).

## Start here

For agentic sessions, start with `project-governance/`.

# Skills

Execution-ready skill catalog for `rise-up`.

Each directory under `skills/` now holds a self-contained playbook rather than a thin pointer to another document.

This tree is the canonical skill content layer.

## What a skill should contain

Every `skills/<skill-name>/SKILL.md` should help an agent or engineer act immediately by covering:

- when to use the skill
- when **not** to use the skill
- the inputs or signals that tell you the skill is relevant
- the outcome it should produce
- the concrete steps to follow
- the narrowest validation to run
- the main pitfalls to avoid
- the key files, commands, and touchpoints involved

## Skill convention used in this repo

For this repository, a skill is a **repeatable operational capability**, not a shelf label and not a redirect.

A skill should be:

- self-contained enough to execute without immediately leaving the file
- narrow enough to be composable with other skills
- durable across sessions
- explicit about boundaries, validation, and handoff

## Required sections

Every canonical skill should, at minimum, answer these questions clearly:

- what mission does this skill serve?
- when should it be used?
- what should it deliver or prove?
- what should the operator do?
- how should the result be validated?
- what common mistakes should be avoided?

## Authoring rule

Prefer adding a new skill only when a routing or execution pattern is reused often enough to justify a stable deep link and a reusable playbook.

If a skill still says little more than “go read another doc,” it is not finished.

Every new skill **must** ship with a paired `.claude/commands/<skill-name>.md` shim in the same commit. The shim is the cross-platform discovery hook — it is what makes the skill invocable as a `/slash-command` in Claude Code and equivalent surfaces on other agentic platforms. A `skills/<name>/SKILL.md` without a matching `.claude/commands/<name>.md` is considered incomplete and must not be merged.


