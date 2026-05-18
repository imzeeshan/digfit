@echo off
setlocal
set "VENV_PY=%~dp0venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    "%VENV_PY%" "%~dp0manage.py" %*
    exit /b %ERRORLEVEL%
)
echo WARNING: venv not found — using system python.
python "%~dp0manage.py" %*
exit /b %ERRORLEVEL%
