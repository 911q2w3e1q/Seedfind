@echo off
chcp 65001 >nul
echo ============================================================
echo   Minecraft 种子查询器 —— Windows 一键打包脚本
echo ============================================================
echo.
echo [1/3] 安装依赖（cubiomes 含原生 C 扩展，首次会自动用 MSVC 编译）
echo       若提示缺少“Microsoft C++ 生成工具”，请按提示安装
echo       “使用 C++ 的桌面开发” 工作负载后重新运行本脚本。
echo.
pip install -r requirements.txt
pip install pyinstaller
if errorlevel 1 (
    echo 依赖安装失败，请检查网络或 Visual Studio 构建工具。
    pause
    exit /b 1
)

echo.
echo [2/3] 使用 PyInstaller 打包为 exe（--collect-all 会带上 cubiomes 原生库）
echo.
pyinstaller -w -D --name MinecraftSeedQuery ^
  --collect-all cubiomespi ^
  --collect-all nbt ^
  --collect-all anvil ^
  --hiddenimport matplotlib.backends.backend_tkagg ^
  --hiddenimport matplotlib.backends.backend_agg ^
  --hiddenimport matplotlib.backends.backend_qt5agg ^
  main.py

if errorlevel 1 (
    echo 打包失败，请查看上方错误信息。
    pause
    exit /b 1
)

echo.
echo [3/3] 完成！exe 位于 dist\MinecraftSeedQuery\MinecraftSeedQuery.exe
echo.
pause
