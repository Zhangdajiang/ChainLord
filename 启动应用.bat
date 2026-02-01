@echo off
chcp 65001 >nul
echo ========================================
echo   我的私人实验室 - 启动脚本
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.12+
    pause
    exit /b 1
)

echo [信息] 正在检查依赖...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo [提示] 检测到缺少依赖，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo [信息] 正在启动应用...
echo [提示] 应用将在浏览器中自动打开
echo [提示] 按 Ctrl+C 可以停止应用
echo.

streamlit run app.py

pause
