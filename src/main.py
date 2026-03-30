"""应用主入口"""

import sys
from pathlib import Path

def main():
    """主入口，支持CLI和GUI模式"""
    if len(sys.argv) > 1:
        # 有命令行参数，运行CLI模式
        from src.cli.main import cli
        cli()
    else:
        # 无命令行参数，默认运行GUI模式
        from src.ui.main_window import run_gui
        run_gui()

if __name__ == "__main__":
    main()
