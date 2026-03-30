"""应用入口"""

import sys
from pathlib import Path

def main():
    """主入口"""
    from src.cli.main import cli
    cli()

if __name__ == "__main__":
    main()
