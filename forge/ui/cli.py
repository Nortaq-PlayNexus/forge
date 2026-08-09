"""Forge CLI — Universal Deploy Engine.

Deploy any stack to any cloud from a single command.
"""

import argparse
import sys
from pathlib import Path

from forge import __version__
from forge.core.detector import detect_stack
from forge.core.provisioner import (
    generate_terraform, generate_dockerfile,
    generate_docker_compose, generate_terraform_modules,
)
from forge.core.estimator import estimate_cost
from forge.core.preview import generate_preview, format_preview
from forge.core.provider_manager import (
    check_provider, get_account_info, list_available_providers,
)
from forge.ui.display import (
    show_banner, show_stack, show_providers, show_preview,
    show_cost, show_generated_files, show_deploy_result,
    show_error, show_warning, show_success, console,
)


def cmd_detect(args):
    """Detect the project stack."""
    show_banner()
    path = Path(args.path) if args.path else Path.cwd()
    stack = detect_stack(path)
    show_stack(stack)
    return 0


def cmd_providers(args):
    """List available cloud providers."""
    show_banner()
    providers = list_available_providers()
    show_providers(providers)
    return 0


def cmd_preview(args):
    """Preview what will be deployed."""
    show_banner()
    path = Path(args.path) if args.path else Path.cwd()
    stack = detect_stack(path)

    show_stack(stack)
    console.print()

    preview = generate_preview(stack, args.provider)
    show_preview(preview)

    est = estimate_cost(stack, args.provider)
    show_cost(est)

    return 0


def cmd_init(args):
    """Initialize deployment files in the project."""
    show_banner()
    path = Path(args.path) if args.path else Path.cwd()
    stack = detect_stack(path)

    show_stack(stack)
    console.print()

    files_written = []

    if not stack.has_docker:
        dockerfile = generate_dockerfile(stack)
        docker_path = path / "Dockerfile"
        if not args.dry_run:
            docker_path.write_text(dockerfile, encoding="utf-8")
        files_written.append(("Dockerfile", dockerfile))

    if len(stack.services) > 0:
        compose = generate_docker_compose(stack)
        compose_path = path / "docker-compose.yml"
        if not args.dry_run:
            compose_path.write_text(compose, encoding="utf-8")
        files_written.append(("docker-compose.yml", compose))

    if not stack.has_terraform:
        modules = generate_terraform_modules(stack, args.provider)
        for fname, content in modules.items():
            fpath = path / fname
            if not args.dry_run:
                fpath.write_text(content, encoding="utf-8")
            files_written.append((fname, content))

    if args.dry_run:
        console.print("[yellow]Dry run — no files written[/yellow]\n")

    show_generated_files(dict(files_written))
    show_success(f"{len(files_written)} files {'previewed' if args.dry_run else 'generated'}")

    return 0


def cmd_deploy(args):
    """Deploy the project."""
    show_banner()
    path = Path(args.path) if args.path else Path.cwd()
    stack = detect_stack(path)

    if not check_provider(args.provider):
        show_error(f"{args.provider.upper()} CLI not available or not configured")
        console.print(f"  Install: https://docs.{args.provider}.amazon.com/cli/latest/userguide/getting-started-install.html")
        return 1

    account = get_account_info(args.provider)
    if account:
        show_success(f"Authenticated to {args.provider.upper()}: {account}")

    show_stack(stack)
    console.print()

    preview = generate_preview(stack, args.provider)
    show_preview(preview)

    est = estimate_cost(stack, args.provider)
    show_cost(est)

    if not args.yes:
        if not console.input("\nProceed with deploy? [y/N] ").strip().lower().startswith("y"):
            show_warning("Deploy cancelled")
            return 0

    console.print("\n[bold cyan]Deploying...[/bold cyan]")

    dockerfile = generate_dockerfile(stack)
    docker_path = path / "Dockerfile"
    if not docker_path.exists() or args.force:
        docker_path.write_text(dockerfile, encoding="utf-8")
        show_success("Dockerfile written")

    modules = generate_terraform_modules(stack, args.provider)
    for fname, content in modules.items():
        fpath = path / fname
        if not fpath.exists() or args.force:
            fpath.write_text(content, encoding="utf-8")
            show_success(f"{fname} written")

    show_deploy_result(True, f"Deployment files generated for {args.provider.upper()}")
    console.print("\n[dim]Next steps:[/dim]")
    console.print(f"  1. Review generated files in {path}")
    console.print(f"  2. Build and push Docker image")
    console.print(f"  3. Run [bold]terraform apply[/bold] to provision infrastructure")

    return 0


def cmd_version(args):
    """Show version info."""
    show_banner()
    console.print(f"Forge v{__version__}")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="forge",
        description="⚡ Forge — Universal Deploy Engine. Deploy any stack to any cloud.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    detect_p = subparsers.add_parser("detect", help="Detect project stack")
    detect_p.add_argument("path", nargs="?", default=".", help="Project path")
    detect_p.set_defaults(func=cmd_detect)

    providers_p = subparsers.add_parser("providers", help="List cloud providers")
    providers_p.set_defaults(func=cmd_providers)

    preview_p = subparsers.add_parser("preview", help="Preview deployment")
    preview_p.add_argument("path", nargs="?", default=".", help="Project path")
    preview_p.add_argument("-p", "--provider", default="aws", choices=["aws", "gcp", "azure"])
    preview_p.set_defaults(func=cmd_preview)

    init_p = subparsers.add_parser("init", help="Generate deployment files")
    init_p.add_argument("path", nargs="?", default=".", help="Project path")
    init_p.add_argument("-p", "--provider", default="aws", choices=["aws", "gcp", "azure"])
    init_p.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    init_p.set_defaults(func=cmd_init)

    deploy_p = subparsers.add_parser("deploy", help="Deploy the project")
    deploy_p.add_argument("path", nargs="?", default=".", help="Project path")
    deploy_p.add_argument("-p", "--provider", default="aws", choices=["aws", "gcp", "azure"])
    deploy_p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    deploy_p.add_argument("-f", "--force", action="store_true", help="Overwrite existing files")
    deploy_p.set_defaults(func=cmd_deploy)

    version_p = subparsers.add_parser("version", help="Show version")
    version_p.set_defaults(func=cmd_version)

    args = parser.parse_args()

    if not args.command:
        show_banner()
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
