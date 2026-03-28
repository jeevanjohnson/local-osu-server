import subprocess
from pathlib import Path

async def is_update_available() -> str | None:
    """Check if there are any local changes compared to the latest release."""
    try:
        if not Path(".git").exists():
            return None
        
        # Get latest tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            cwd=Path("."),
        )
        latest_tag = result.stdout.strip()
        if not latest_tag:
            return None
        
        # Check if there are differences between current code and latest tag
        diff_result = subprocess.run(
            ["git", "diff", latest_tag],
            capture_output=True,
            text=True,
            cwd=Path("."),
        )
        
        # If there's output, there are differences (update available)
        if diff_result.stdout.strip():
            return latest_tag
        
        return None
    except Exception:
        return None


async def update() -> str:
    """Update to latest release, overwriting any local changes."""
    try:
        if not Path(".git").exists():
            return "Error: Not a git repository."
        
        # Get latest tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            cwd=Path("."),
        )
        latest_tag = result.stdout.strip()
        if not latest_tag:
            return "Error: Could not find release tag."
        
        # Reset hard to discard all local changes
        subprocess.run(
            ["git", "reset", "--hard"],
            capture_output=True,
            cwd=Path("."),
        )
        
        # Checkout latest tag
        result = subprocess.run(
            ["git", "checkout", latest_tag],
            capture_output=True,
            text=True,
            cwd=Path("."),
        )
        
        if result.returncode == 0:
            return f"Successfully updated to {latest_tag}! Please restart the server."
        else:
            return f"Update failed: {result.stderr}"
    
    except Exception as e:
        return f"Update failed: {str(e)}"
    