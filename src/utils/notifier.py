"""
macOS notification helper using osascript.
"""

import subprocess


def notify(title: str, message: str = "", subtitle: str = "") -> None:
    """Send a native macOS notification."""
    script = f'display notification "{message}" with title "{title}"'
    if subtitle:
        script += f' subtitle "{subtitle}"'
    subprocess.Popen(["osascript", "-e", script])
