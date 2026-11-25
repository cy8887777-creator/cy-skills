@echo off
setlocal
python "%~dp0scripts\validate.py" %*
exit /b %errorlevel%
