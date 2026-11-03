@echo off
rem Bootstrap: requires Python 3.8+ -> https://www.python.org/downloads/ (or: winget install Python.Python.3.12)
python "%~dp0install.py" %* 2>nul && goto :eof
curl -fsSL -H "Accept: application/vnd.github.raw" -H "User-Agent: devin-agentic" "https://api.github.com/repos/JoShMiQueL/devin-agentic/contents/install.py" -o "%TEMP%\da-install.py" && python "%TEMP%\da-install.py" %*
if errorlevel 1 echo Python not found - install it: https://www.python.org/downloads/ & exit /b 1
