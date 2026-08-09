"""Deployment preview generator.

Generates a preview of what will be deployed before execution.
"""

from typing import Optional


def generate_preview(stack, provider: str, config: Optional[dict] = None) -> dict:
    """Generate deployment preview."""
    config = config or {}

    preview = {
        "project": stack.path.name,
        "stack": stack.stack_label,
        "language": stack.primary_language,
        "framework": stack.primary_framework,
        "port": stack.port,
        "provider": provider,
        "services": stack.services,
        "files_to_generate": [],
        "resources": [],
        "estimated_monthly_cost": None,
    }

    if not stack.has_docker:
        preview["files_to_generate"].append("Dockerfile")

    if not stack.has_terraform:
        preview["files_to_generate"].append("main.tf")
        preview["files_to_generate"].append("variables.tf")
        preview["files_to_generate"].append("outputs.tf")

    if len(stack.services) > 0 and not any(
        (stack.path / f).exists() for f in ["docker-compose.yml", "docker-compose.yaml"]
    ):
        preview["files_to_generate"].append("docker-compose.yml")

    provider_resources = {
        "aws": ["ECS Fargate Cluster", "ECR Repository", "Task Definition"],
        "gcp": ["Cloud Run Service", "Artifact Registry"],
        "azure": ["Container Instance", "Resource Group", "Container Registry"],
    }

    preview["resources"] = provider_resources.get(provider, [])

    if stack.services:
        if any(s in stack.services for s in ["postgres", "mysql", "mongo"]):
            preview["resources"].append("Managed Database")
        if "redis" in stack.services:
            preview["resources"].append("Managed Cache")

    return preview


def format_preview(preview: dict) -> str:
    """Format preview as readable text."""
    lines = []
    lines.append(f"  Project:    {preview['project']}")
    lines.append(f"  Stack:      {preview['stack']}")
    lines.append(f"  Provider:   {preview['provider'].upper()}")
    lines.append(f"  Port:       {preview['port'] or 'auto-detect'}")

    if preview["services"]:
        lines.append(f"  Services:   {', '.join(preview['services'])}")

    if preview["files_to_generate"]:
        lines.append("")
        lines.append("  Files to generate:")
        for f in preview["files_to_generate"]:
            lines.append(f"    + {f}")

    if preview["resources"]:
        lines.append("")
        lines.append("  Cloud resources:")
        for r in preview["resources"]:
            lines.append(f"    ~ {r}")

    return "\n".join(lines)
