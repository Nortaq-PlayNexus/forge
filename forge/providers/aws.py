"""AWS provider operations."""

import subprocess


def check_aws_cli() -> bool:
    """Check if AWS CLI is installed and configured."""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_account_id() -> str | None:
    """Get current AWS account ID."""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_regions() -> list[str]:
    """Get available AWS regions."""
    try:
        result = subprocess.run(
            [
                "aws",
                "ec2",
                "describe-regions",
                "--query",
                "Regions[].RegionName",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip().split()
    except Exception:
        pass
    return ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]


def ecr_login(region: str = "us-east-1") -> str | None:
    """Get ECR login token and endpoint."""
    try:
        result = subprocess.run(
            ["aws", "ecr", "get-login-password", "--region", region],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None
