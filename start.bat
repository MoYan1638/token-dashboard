@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Token 消耗看板
echo ============================================
echo.
echo  浏览器会自动打开，页面上有绿色「实时扫描中」
echo  标识即为实时版。关闭本窗口即停止服务。
echo.
python -m tokenboard %*
pause
