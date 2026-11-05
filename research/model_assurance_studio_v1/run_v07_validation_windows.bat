@echo off
cd /d "%~dp0"
python scripts\verify_v07_release.py
if errorlevel 1 (
  echo.
  echo Validation FAILED.
  pause
  exit /b 1
)
echo.
echo Local evidence replay succeeded. Lean and official ONNX Runtime remain separate checks.
pause
