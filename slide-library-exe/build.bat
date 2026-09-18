@echo off
rem Builds dist\SlideLibrary.exe (or dist\SlideLibrary\ with "build.bat onedir").
rem Needs Python 3.10+ on PATH (python.org installer, "py" launcher is fine). Run on Windows.
setlocal
cd /d "%~dp0"

where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% -m venv .venv-build || goto :fail
call .venv-build\Scripts\activate.bat || goto :fail
python -m pip install --quiet --upgrade pip || goto :fail
python -m pip install --quiet -r requirements-build.txt || goto :fail

if /i "%~1"=="onedir" set "SLIDELIB_ONEDIR=1"
pyinstaller --clean --noconfirm slide_library.spec || goto :fail

echo.
if /i "%~1"=="onedir" (echo Built: %~dp0dist\SlideLibrary\SlideLibrary.exe) else (echo Built: %~dp0dist\SlideLibrary.exe)
exit /b 0

:fail
echo.
echo BUILD FAILED
exit /b 1
