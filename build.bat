@echo off
chcp 65001 >nul
echo ================================
echo ComicMeta Editor 构建脚本
echo ================================
echo.

echo [1/4] 清理之前的构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo 清理完成！
echo.

echo [2/4] 检查 PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller 未安装，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo 安装失败！请手动运行: pip install pyinstaller
        pause
        exit /b 1
    )
)
echo PyInstaller 已就绪！
echo.

echo [3/4] 开始构建可执行文件...
set PYTHONPATH=%CD%
for /f "delims=" %%i in ('python -c "from core._version import __version__; print(__version__)"') do set APP_VERSION=%%i

if "%APP_VERSION%"=="" (
    echo 错误: 无法获取版本号！
    pause
    exit /b 1
)
echo 当前版本: %APP_VERSION%

pyinstaller ComicMetaEditor.spec
if errorlevel 1 (
    echo 构建失败！请检查错误信息。
    pause
    exit /b 1
)



echo 构建完成！
echo.

echo [4/4] 构建成功！
echo.
echo 输出目录: dist\ComicMetaEditor
echo 可执行文件: dist\ComicMetaEditor\ComicMetaEditor.exe
echo.
pause
