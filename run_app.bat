@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 main.py %*
) else (
  python main.py %*
)
if errorlevel 1 (
  echo.
  echo The app could not start. Make sure Python 3.12+ and dependencies are installed:
  echo   py -3 -m pip install -r requirements.txt
  echo   or: py -3 -m pip install PySide6 matplotlib platformdirs reportlab
  echo.
  pause
)
