"""MCLauncherHelper 桌面版入口。

打包：pyinstaller --noconfirm --onefile --windowed --name MCLauncherHelper main.py
"""
import sys
from pathlib import Path

# 确保直接运行时（非打包）能找到 src 包
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.app_gui import main

if __name__ == "__main__":
    main()
