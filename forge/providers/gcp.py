"""GCP provider operations."""

import subprocess


def check_gcloud_cli() -> bool:
    """Check if gcloud CLI is installed and configured."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "list"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_project() -> str | None:
    """Get current GCP project."""
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_regions() -> list[str]:
    """Get available GCP regions."""
    return ["us-central1", "us-east1", "europe-west1", "asia-southeast1"]
