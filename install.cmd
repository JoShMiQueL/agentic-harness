@echo off
rem devin-agentic installer for cmd.exe — thin wrapper over install.ps1.
rem One-liner equivalent:
rem   powershell -NoProfile -Command "irm https://cdn.jsdelivr.net/gh/JoShMiQueL/devin-agentic@main/install.ps1 | iex"
setlocal
set "PS=%~dp0install.ps1"
if not exist "%PS%" (
  echo install.ps1 not found next to this script. Use the powershell one-liner instead:
  echo   powershell -NoProfile -Command "irm https://cdn.jsdelivr.net/gh/JoShMiQueL/devin-agentic@main/install.ps1 ^| iex"
  exit /b 1
)
where pwsh >nul 2>&1 && (set "SH=pwsh") || (set "SH=powershell")
"%SH%" -NoProfile -ExecutionPolicy Bypass -File "%PS%" %*
exit /b %errorlevel%
