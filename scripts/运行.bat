@echo off
REM 运行FileFinder的启动脚本
REM 此脚本会尝试用Python直接运行程序

setlocal enabledelayedexpansion

REM 获取脚本所在目录并切到项目根目录
set SCRIPT_DIR=%~dp0
set ROOT=%SCRIPT_DIR%..

REM 尝试找到Python
for /f "delims=" %%i in ('where python 2^>nul') do (
    set PYTHON=%%i
    goto found_python
)

REM 如果未找到，尝试常见位置
if not defined PYTHON (
    if exist "C:\Python39\python.exe" (
        set PYTHON=C:\Python39\python.exe
    ) else if exist "C:\Python310\python.exe" (
        set PYTHON=C:\Python310\python.exe
    ) else if exist "C:\Python311\python.exe" (
        set PYTHON=C:\Python311\python.exe
    )
)

:found_python

if not defined PYTHON (
    echo [错误] 未找到Python环境
    echo.
    echo 请按以下步骤操作:
    echo 1. 访问 https://www.python.org/downloads/
    echo 2. 下载 Python 3.9 或更新版本
    echo 3. 安装时请勾选 "Add Python to PATH"
    echo 4. 重新运行此脚本
    echo.
    pause
    exit /b 1
)

REM 运行程序
"%PYTHON%" "%ROOT%\src\app.py"
if errorlevel 1 (
    echo.
    echo [错误] 程序运行失败
    pause
)
