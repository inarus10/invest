@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo ==========================================================
echo   [포트폴리오 모멘텀 리밸런싱 자동 실행기]
echo ==========================================================
echo.

if "%~1"=="" (
    :: 인자 없이 더블클릭한 경우: 기본 실행 (15일/말일 자동 판별 + 웹브라우저 오픈 + GitHub 자동 푸시)
    .venv\Scripts\python.exe main.py --open --push
) else (
    :: 인자가 전달된 경우 (예: --force, --date 2026-09-30 등)
    .venv\Scripts\python.exe main.py --open --push %*
)

echo.
echo ==========================================================
pause
