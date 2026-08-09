"""Cloud provider manager."""

from typing import Optional
from forge.providers import aws, gcp, azure


PROVIDERS = {
    "aws": {
        "check": aws.check_aws_cli,
        "account": aws.get_account_id,
        "regions": aws.get_regions,
        "label": "Amazon Web Services",
    },
    "gcp": {
        "check": gcp.check_gcloud_cli,
        "account": gcp.get_project,
        "regions": gcp.get_regions,
        "label": "Google Cloud Platform",
    },
    "azure": {
        "check": azure.check_az_cli,
        "account": azure.get_subscription,
        "regions": azure.get_locations,
        "label": "Microsoft Azure",
    },
}


def check_provider(name: str) -> bool:
    """Check if a provider CLI is available and configured."""
    provider = PROVIDERS.get(name)
    if not provider:
        return False
    return provider["check"]()


def get_account_info(name: str) -> Optional[str]:
    """Get account/project ID for a provider."""
    provider = PROVIDERS.get(name)
    if not provider:
        return None
    return provider["account"]()


def list_available_providers() -> list[dict]:
    """List all providers and their availability."""
    results = []
    for name, info in PROVIDERS.items():
        available = info["check"]()
        account = info["account"]() if available else None
        results.append({
            "name": name,
            "label": info["label"],
            "available": available,
            "account": account,
        })
    return results
