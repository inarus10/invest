@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo ==========================================================
echo   [포트폴리오 모멘텀 리밸런싱 자동 실행기]
echo ==========================================================
echo.

if "%~1"=="" (
    :: 인자 없이 더블클릭한 경우: 일반 실행 (오늘이 15일 또는 말일이면 자동 실행)
    .venv\Scripts\python.exe main.py --open
    
    :: 만약 15일/말일이 아니라서 아무 작업도 안 되었다면 강제 실행 선택지 제공
    if %ERRORLEVEL% EQU 0 (
        goto :end
    )
) else (
    :: 인자가 전달된 경우 그대로 실행
    .venv\Scripts\python.exe main.py --open %*
)

:end
echo.
echo ==========================================================
pause
