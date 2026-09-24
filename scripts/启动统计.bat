@echo off
cd /d "%~dp0.."
rem Resolve a pythonw that has tkinter. Prefer per-user Python install (no username in source), fall back to PATH.
set "PYW=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
if not exist "%PYW%" for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\pythonw.exe" set "PYW=%%D\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw.exe"
"%PYW%" "src\deskpet.py"
