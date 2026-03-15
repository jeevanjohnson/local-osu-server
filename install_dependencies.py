"""
Purpose/Domain/Concept:
- Ensures all the necessary dependencies for the application are installed.
"""

import subprocess
import sys

def install_dependencies():
    print("Installing dependencies...")

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Failed to install dependencies:")
        print(result.stderr)
        sys.exit(1)
    
    print("Dependencies installed successfully.")