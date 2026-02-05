@echo off
chcp 65001 >nul
echo ====================================
echo 开始编译 FileFinder.exe
echo ====================================
echo.

REM 检查是否有旧的exe文件正在运行
tasklist /FI "IMAGENAME eq FileFinder.exe" 2>NUL | find /I /N "FileFinder.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo 检测到 FileFinder.exe 正在运行，正在关闭...
    taskkill /F /IM FileFinder.exe 2>NUL
    timeout /t 2 /nobreak >NUL
)

REM 获取脚本所在目录并切到项目根目录
set SCRIPT_DIR=%~dp0
set ROOT=%SCRIPT_DIR%..
pushd "%ROOT%"

REM 删除旧的构建文件
echo 清理旧的构建文件...
if exist "build" rmdir /s /q build
if exist "dist\FileFinder.exe" del /f /q dist\FileFinder.exe
echo.

REM 开始编译
echo 正在编译，请稍候...
echo.
pyinstaller --onefile --windowed --icon=assets\icon.ico --name=FileFinder src\app.py

echo.
if exist "dist\FileFinder.exe" (
    echo ====================================
    echo 编译成功！
    echo 可执行文件位置: dist\FileFinder.exe
    echo ====================================
    echo 正在打开可执行文件夹...
    start "" "dist"
) else (
    echo ====================================
    echo 编译失败，请检查错误信息
    echo ====================================
)

echo.
popd
pause
