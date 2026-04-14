@echo off
chcp 65001 >nul
echo ========================================
echo   300英雄 占卜自动化 - 打包工具
echo ========================================
echo.

pip install pyinstaller >nul 2>&1

echo 正在打包...

python -m PyInstaller --onefile --windowed ^
    --name "酸败好运星盘" ^
    --add-data "temp;temp" ^
    --uac-admin ^
    --icon icon.ico ^
    --version-file version_info.py ^
    --hidden-import mss ^
    --hidden-import mss.windows ^
    --noconfirm ^
    gui.py

echo.
if exist "dist\酸败好运星盘.exe" (
    echo ========================================
    echo   打包成功!
    echo   输出: dist\酸败好运星盘.exe
    echo ========================================
) else (
    echo 打包失败，请检查错误信息
)
pause
