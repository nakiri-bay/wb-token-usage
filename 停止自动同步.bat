@echo off
cd /d "%~dp0"
:: 读取 auto_sync.pid 并结束对应的 pythonw 进程（无窗口守护）
if not exist auto_sync.pid (
  echo 未找到 auto_sync.pid，自动同步可能未运行。
  pause
  exit /b
)
set /p PID=<auto_sync.pid
echo 正在停止自动同步进程 pid=%PID% ...
taskkill /pid %PID% /f
if exist auto_sync.pid del auto_sync.pid
echo 已停止。
pause
