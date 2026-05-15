@echo off
cd /d "%~dp0"
echo Running FinAnalysis...
uv run python -m src.main
pause
