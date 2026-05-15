---
name: shell-conventions
description: Shell script coding standards — Bash conventions, module system, environment setup. Use when writing or modifying shell scripts.
---

# Skill: Shell Script Conventions

## Formatting & Linting
- Format: `/proj/lte_twh/tools/shfmt/latest/bin/shfmt -l -i 4 -ci -fn -ln=auto -w <file_path>`
- Check: Run `module avail shellcheck` to find the latest version, then `module add shellcheck/<version>`, then `shellcheck <file_path>`
- Always run `shfmt` and `shellcheck` on any modified shell script before committing

## Standards
- Use `#!/bin/bash` or `#!/bin/sh` shebang
- Use functions for logical grouping
- Add comments for non-obvious logic
- Use `set -e` or explicit error handling
- Quote variables: `"$VAR"` not `$VAR`

## Environment
- `ERBS_ROOT` — MOM repository root (set via `source gitenv.sh`)
- `MOM_ROOT` — Alternative root used by autoWorkflow
- Add modules: `module add <package_name>`
- Check available: `module avail <package_name>` — if not found, try `module avail -a | grep <package_name>`

## Common Patterns
- Validate input parameters at script start
- Use `pushd`/`popd` for directory changes
- Clean up temp files via `trap cleanup EXIT`
- Use `tee -a` for logging to both stdout and file
