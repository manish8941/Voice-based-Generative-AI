"""
Voice-to-Insight System: Main Entry Point
Launches the PyQt6 graphical user interface or dispatches to CLI mode if arguments are provided.
"""

import sys
from src.ui.main_window import run_gui
from src.cli import main as run_cli

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # CLI Mode
        run_cli()
    else:
        # GUI Mode
        run_gui()
