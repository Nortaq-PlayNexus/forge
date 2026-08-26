"""Cloud provider manager."""


from forge.providers import aws, azure, gcp

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


def get_account_info(name: str) -> str | None:
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


def check_provider_health(name: str) -> dict:
    """Verify provider is reachable and quotas are OK."""
    provider = PROVIDERS.get(name)
    if not provider:
        return {"name": name, "reachable": False, "error": "Unknown provider"}

    try:
        available = provider["check"]()
        if not available:
            return {"name": name, "reachable": False, "error": "CLI not configured"}

        account = provider["account"]()
        return {
            "name": name,
            "reachable": True,
            "account": account,
            "error": None,
        }
    except Exception as e:
        return {"name": name, "reachable": False, "error": str(e)}


def get_provider_limits(name: str) -> dict:
    """Get service limits (EC2 instances, RDS, etc.)."""
    limits = {
        "aws": {
            "ec2_instances": {"limit": 20, "used": 0, "unit": "instances"},
            "rds_instances": {"limit": 40, "used": 0, "unit": "instances"},
            "elasticache": {"limit": 50, "used": 0, "unit": "clusters"},
            "s3_buckets": {"limit": 100, "used": 0, "unit": "buckets"},
            "vpcs": {"limit": 5, "used": 0, "unit": "VPCs"},
        },
        "gcp": {
            "compute_instances": {"limit": 24, "used": 0, "unit": "instances"},
            "cloud_sql": {"limit": 40, "used": 0, "unit": "instances"},
            "memorystore": {"limit": 50, "used": 0, "unit": "instances"},
            "buckets": {"limit": 100, "used": 0, "unit": "buckets"},
            "networks": {"limit": 5, "used": 0, "unit": "networks"},
        },
        "azure": {
            "virtual_machines": {"limit": 20, "used": 0, "unit": "VMs"},
            "sql_servers": {"limit": 50, "used": 0, "unit": "servers"},
            "redis_cache": {"limit": 50, "used": 0, "unit": "instances"},
            "storage_accounts": {"limit": 100, "used": 0, "unit": "accounts"},
            "virtual_networks": {"limit": 50, "used": 0, "unit": "VNets"},
        },
    }
    return limits.get(name, {"error": f"Limits not available for {name}"})


def list_regions(name: str) -> list[dict]:
    """Unified region listing across providers."""
    provider = PROVIDERS.get(name)
    if not provider:
        return []
    try:
        regions = provider["regions"]()
        if isinstance(regions, list):
            return [{"name": r} if isinstance(r, str) else r for r in regions]
        return []
    except Exception:
        return []
