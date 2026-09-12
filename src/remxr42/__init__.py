"""
remxr42 - Dual Circular Polar Vinyl DJ Workstation
A Teenage Engineering-inspired turntable console with 2D circular polar spectrograms,
time-frequency conversion lab, and real-time audio scratching.
"""

__version__ = "1.0.0"
__all__ = ["spectrogram_engine", "console_component", "cli", "main"]

def main():
    from remxr42.cli import main as cli_main
    cli_main()
