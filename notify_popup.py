"""
Windows popup notification helper for Jimeng batch runner.
Uses PowerShell + System.Windows.Forms.MessageBox for reliable desktop popups.
"""
import subprocess
import sys


def notify(title: str, message: str, blocking: bool = False) -> None:
    """Show a popup notification via PowerShell MessageBox."""
    escaped_title = title.replace("'", "''")
    escaped_message = message.replace("'", "''")
    ps_cmd = (
        f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
        f"[System.Windows.Forms.MessageBox]::Show('{escaped_message}', '{escaped_title}', 'OK', 'Information')"
    )
    if blocking:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            timeout=300,
        )
    else:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )


if __name__ == "__main__":
    title = sys.argv[1] if len(sys.argv) > 1 else "Jimeng Video"
    message = sys.argv[2] if len(sys.argv) > 2 else "Task completed!"
    notify(title, message, blocking=True)
