@echo off
rem Windows 启动器：双击=立即发一轮；测试请在 cmd 里运行 send.bat --test
chcp 65001 >nul
cd /d "%~dp0.."
python send.py %*
pause
