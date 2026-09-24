@echo off
cd /d "%~dp0.."
:: 结束「独立同步守护」进程（仅在用过 auto_sync.vbs 时才需要）
:: 若你用的是桌宠自带的同步，请直接右键桌宠 -> 退出统计（同步会一并停止）
if not exist auto_sync.pid (
  echo 未找到 auto_sync.pid：独立同步守护未在运行。
  echo 若你在用桌宠自带的同步，直接右键桌宠 -^> 退出统计 即可。
  pause
  exit /b
)
set /p PID=<auto_sync.pid
echo 正在停止独立同步守护 pid=%PID% ...
taskkill /pid %PID% /f
if exist auto_sync.pid del auto_sync.pid
echo 已停止。
pause
