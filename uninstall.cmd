@echo off
python "%~dp0uninstall.py" %* || (echo Python not found - https://www.python.org/downloads/ & exit /b 1)
