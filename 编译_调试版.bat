@echo off
chcp 65001 >nul

echo ====================================
echo 开始编译 FileFinder_Debug.exe (调试版)
echo ====================================
echo.
echo 注意：此版本会显示控制台窗口和调试信息
echo.

REM 检查是否有旧的exe文件正在运行
tasklist /FI "IMAGENAME eq FileFinder_Debug.exe" 2>NUL | find /I /N "FileFinder_Debug.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo 检测到 FileFinder_Debug.exe 正在运行，正在关闭...
    taskkill /F /IM FileFinder_Debug.exe 2>NUL
    timeout /t 2 /nobreak >NUL
)

REM 删除旧的构建文件
echo 清理旧的构建文件...
if exist "build" rmdir /s /q build
if exist "dist\FileFinder_Debug.exe" del /f /q dist\FileFinder_Debug.exe
echo.

REM 开始编译（移除 --windowed 参数，显示控制台）
echo 正在编译调试版本，请稍候...
echo.
pyinstaller --onefile --icon=assets\icon.ico --name=FileFinder_Debug src\app.py

echo.
if exist "dist\FileFinder_Debug.exe" (
    echo ====================================
    echo 编译成功！
    echo 可执行文件位置: dist\FileFinder_Debug.exe
    echo ====================================
    echo.
    echo 运行此版本时会显示控制台窗口，可以看到：
    echo - 配置文件加载信息
    echo - 版本迁移过程
    echo - 错误和警告信息
    echo ====================================
) else (
    echo ====================================
    echo 编译失败，请检查错误信息
    echo ====================================
)

echo.
pause
