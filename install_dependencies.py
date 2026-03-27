import subprocess
import sys


def install_dependencies():
    print("Installing dependencies...")

    print("Installing requirements...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Failed to install Playwright browsers:")
        print(result.stderr)
        sys.exit(1)

    print("Dependencies installed successfully.")
