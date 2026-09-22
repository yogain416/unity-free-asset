@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Unity Free Asset 설치 ===

where python >nul 2>&1
if errorlevel 1 (
  echo Python이 없습니다. https://www.python.org/downloads/ 에서 설치할 때 "Add python.exe to PATH"를 체크하세요.
  pause & exit /b 1
)

echo [1/4] 가상환경 만들기
if not exist .venv python -m venv .venv || (echo 실패 & pause & exit /b 1)

echo [2/4] Playwright 설치
.venv\Scripts\python -m pip install -q -r requirements.txt || (echo 실패 & pause & exit /b 1)
.venv\Scripts\python -m playwright install chromium || (echo 실패 & pause & exit /b 1)

echo [3/4] Unity 로그인 - 뜨는 Chrome 창에서 로그인하세요. 스토어로 돌아오면 자동으로 닫힙니다.
set PYTHONIOENCODING=utf-8
.venv\Scripts\python claim.py --login || (echo 로그인 실패. login.bat 으로 다시 시도하세요. & pause & exit /b 1)

echo [4/4] 작업 스케줄러 등록 (매일 12:00)
powershell -NoProfile -ExecutionPolicy Bypass -File register_task.ps1 || (echo 실패 & pause & exit /b 1)

echo.
echo 설치 완료. 지금 한 번 실행해서 확인합니다...
.venv\Scripts\python claim.py
echo.
echo 위에 "성공" 또는 "이미 보유 중" 이 보이면 끝입니다. 이후엔 매일 12:00에 자동으로 돕니다.
pause
