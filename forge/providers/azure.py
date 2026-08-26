"""Azure provider operations."""

import subprocess


def check_az_cli() -> bool:
    """Check if Azure CLI is installed and configured."""
    try:
        result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_subscription() -> str | None:
    """Get current Azure subscription ID."""
    try:
        result = subprocess.run(
            ["az", "account", "show", "--query", "id", "--output", "tsv"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_locations() -> list[str]:
    """Get available Azure locations."""
    return ["eastus", "westus2", "westeurope", "southeastasia"]
