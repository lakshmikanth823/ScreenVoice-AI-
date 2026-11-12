@echo off
echo ============================================
echo   GameVocalize - Setup Script
echo ============================================
echo.

set PYTHON=python

echo [1/2] Installing core dependencies...
%PYTHON% -m pip install dxcam mss opencv-python numpy Pillow keyboard mouse pystray pywin32 customtkinter rapidocr_onnxruntime onnxruntime
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/2] Verifying installation...
%PYTHON% -c "import dxcam; print('  [OK] dxcam')"
%PYTHON% -c "import mss; print('  [OK] mss')"
%PYTHON% -c "import cv2; print('  [OK] opencv')"
%PYTHON% -c "import numpy; print('  [OK] numpy')"
%PYTHON% -c "import keyboard; print('  [OK] keyboard')"
%PYTHON% -c "import pystray; print('  [OK] pystray')"
%PYTHON% -c "import win32com.client; print('  [OK] pywin32')"
%PYTHON% -c "import customtkinter; print('  [OK] customtkinter')"
%PYTHON% -c "from rapidocr_onnxruntime import RapidOCR; print('  [OK] rapidocr_onnxruntime')"

echo.
echo ============================================
echo   Setup complete!
echo   Run Start_GameVocalize.bat to launch.
echo ============================================
pause
