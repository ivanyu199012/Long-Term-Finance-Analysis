---
name: python-conventions
description: Python coding standards — PEP 8, docstrings, type hints, ruff formatting, module system for packages. Use when writing or modifying Python files.
---

# Skill: Python Conventions

## Standards
- Follow PEP 8
- All functions and classes must have docstrings
- Use type hints for function parameters and return values

## Formatting & Linting
- Format: `/proj/lte_twh/tools/ruff/latest/bin/ruff format --line-length 120 <file>`
- Check: `/proj/lte_twh/tools/ruff/latest/bin/ruff check <file>`
- Always run `ruff format` on any modified Python file before committing
- Always run `ruff check` after formatting to verify no issues remain

## Package Management
- Check availability: `module avail <package_name>` — if not found, try `module avail -a | grep <package_name>`
- Add package: `module add <package_name>`
- Always add the base Python version package alongside any addon: `module add python/3.11.12 python/3.11-addons-<lib>-<ver>`
- Only add one Python version package (e.g., `python/3.11.12`) — do not mix versions
- Common packages: `python/3.11.12`, `python/3.11-addons-openpyxl-3.1.2`, `python/3.11-addons-requests-2.28.2`
