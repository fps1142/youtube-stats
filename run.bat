@echo off
chcp 65001 > nul
echo ===================================================
echo   YouTube 相場予想集計システム 起動中...
echo ===================================================
echo.
echo ブラウザで http://127.0.0.1:8000 を開きます。
echo 終了する場合は、このウィンドウで Ctrl+C を押してください。
echo.

start "" "http://127.0.0.1:8000"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
