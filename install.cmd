@echo off
rem devin-agentic installer for cmd.exe — self-bootstrapping wrapper.
rem Remote one-liner:
rem   curl -fsSL https://cdn.jsdelivr.net/gh/JoShMiQueL/devin-agentic@main/install.cmd -o install.cmd && install.cmd && del install.cmd
setlocal
if exist "%~dp0devin-home\agents" (
  set "PS1=%~dp0install.ps1"
) else (
  set "PS1=%TEMP%\devin-agentic-install.ps1"
  curl -fsSL "https://cdn.jsdelivr.net/gh/JoShMiQueL/devin-agentic@main/install.ps1" -o "%PS1%" || (
    echo download of install.ps1 failed >&2 & exit /b 1 )
)
where pwsh >nul 2>&1 && (set "SH=pwsh") || (set "SH=powershell")
"%SH%" -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
exit /b %errorlevel%
