@echo off
rem devin-agentic installer for cmd.exe — self-bootstrapping wrapper.
rem Remote one-liner:
rem   curl -fsSL https://cdn.jsdelivr.net/gh/JoShMiQueL/devin-agentic@main/install.cmd -o install.cmd && install.cmd && del install.cmd
setlocal
set "PS1=%~dp0install.ps1"
if not exist "%~dp0devin-home\agents" set "PS1=%TEMP%\devin-agentic-install.ps1"
if "%PS1%"=="%~dp0install.ps1%" goto run
curl -fsSL -H "Accept: application/vnd.github.raw" -H "User-Agent: devin-agentic" "https://api.github.com/repos/JoShMiQueL/devin-agentic/contents/install.ps1" -o "%PS1%" || (
  echo download of install.ps1 failed >&2 & exit /b 1 )
:run
where pwsh >nul 2>&1 && (set "SH=pwsh") || (set "SH=powershell")
"%SH%" -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
exit /b %errorlevel%
