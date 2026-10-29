@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 未找到项目虚拟环境，请先按 README.md 安装依赖。
  pause
  exit /b 1
)
echo 启动后请在浏览器打开 http://127.0.0.1:8765
echo 关闭此窗口将结束网页服务。
".venv\Scripts\python.exe" -X utf8 -m src.xiaoying_agent.web
pause
