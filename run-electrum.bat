@echo off
title Electrum-SMART 3.0.0
echo.
echo Electrum-SMART 3.0.0 - SmartCash Thin Client
echo ============================================
echo.
if not exist "venv\" (
    echo Creating Python virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install ecdsa pyaes qrcode pbkdf2 jsonrpclib pysocks pycryptodomex
    pip install PyQt5
) else (
    call venv\Scripts\activate.bat
)
echo.
echo Electrum-SMART starten...
python electrum-smart
pause
