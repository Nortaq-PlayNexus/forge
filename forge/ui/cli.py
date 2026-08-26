"""Forge CLI — Universal Deploy Engine.

Deploy any stack to any cloud from a single command.
"""

import argparse
import sys
from pathlib import Path

from forge import __version__
from forge.core.detector import detect_stack
from forge.core.estimator import compare_providers, estimate_cost, estimate_reserved, estimate_spot
from forge.core.preview import generate_preview
from forge.core.provider_manager import (
    check_provider,
    get_account_info,
    list_available_providers,
)
from forge.core.provisioner import (
    generate_docker_compose,
    generate_dockerfile,
    generate_github_actions,
    generate_gitlab_ci,
    generate_terraform_modules,
)
from forge.core.rollback import RollbackManager
from forge.core.secrets import SecretsManager
from forge.ui.display import (
    console,
    print_ci_config,
    print_cost_comparison,
    print_rollback_options,
    show_banner,
    show_cost,
    show_deploy_result,
    show_error,
    show_generated_files,
    show_preview,
    show_providers,
    show_stack,
    show_success,
    show_warning,
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
    console.print("  2. Build and push Docker image")
    console.print("  3. Run [bold]terraform apply[/bold] to provision infrastructure")

    return 0


def cmd_version(args):
    """Show version info."""
    show_banner()
    console.print(f"Forge v{__version__}")
    return 0


def cmd_rollback(args):
    """Rollback to a previous snapshot."""
    show_banner()
    mgr = RollbackManager()
    snapshots = mgr.list_snapshots()
    if not snapshots:
        show_warning("No snapshots found. Deploy something first.")
        return 0

    print_rollback_options(snapshots)

    if args.snapshot_id:
        snap_id = args.snapshot_id
    else:
        snap_id = console.input("\nEnter snapshot ID to restore (or 'q' to cancel): ").strip()
        if snap_id.lower() == "q":
            show_warning("Rollback cancelled")
            return 0

    try:
        state = mgr.rollback(snap_id)
        show_success(f"Restored snapshot {snap_id}")
        console.print(f"  State keys: {', '.join(state.keys())}")
    except FileNotFoundError as e:
        show_error(str(e))
        return 1
    return 0


def cmd_snapshots(args):
    """List deployment snapshots."""
    show_banner()
    mgr = RollbackManager()
    snapshots = mgr.list_snapshots()
    if not snapshots:
        show_warning("No snapshots found.")
        return 0
    print_rollback_options(snapshots)
    return 0


def cmd_secrets_init(args):
    """Initialize secrets management."""
    show_banner()
    mgr = SecretsManager()
    result = mgr.init_secrets()
    show_success(f"Secrets initialized: {result['key_file']}")
    return 0


def cmd_secrets_validate(args):
    """Validate .env file."""
    show_banner()
    mgr = SecretsManager()
    issues = mgr.validate_env_file(args.path)
    if not issues:
        show_success("No issues found in .env file")
    else:
        console.print(f"[yellow]Found {len(issues)} issue(s):[/yellow]")
        for issue in issues:
            console.print(f"  Line {issue['line']}: {issue['issue']} ({issue['value']})")
    return 0


def cmd_compare(args):
    """Compare costs across providers."""
    show_banner()
    path = Path(args.path) if args.path else Path.cwd()
    stack = detect_stack(path)
    show_stack(stack)
    console.print()

    comparisons = compare_providers(stack, args.tier)
    print_cost_comparison(comparisons)

    if args.reserved:
        console.print("\n[bold cyan]Reserved Instance Estimates:[/bold cyan]")
        for years in (1, 3):
            est = estimate_reserved(stack, comparisons[0]["provider"], years)
            console.print(f"  {years}yr reserved ({comparisons[0]['provider'].upper()}): ${est.total:.2f}/mo")

    if args.spot:
        console.print("\n[bold cyan]Spot Instance Estimates:[/bold cyan]")
        est = estimate_spot(stack, comparisons[0]["provider"])
        console.print(f"  Spot ({comparisons[0]['provider'].upper()}): ${est.total:.2f}/mo")

    return 0


def cmd_ci(args):
    """Generate CI/CD configuration."""
    show_banner()
    path = Path(args.path) if args.path else Path.cwd()
    stack = detect_stack(path)

    files_written = {}

    if args.github or not args.gitlab:
        gh = generate_github_actions(stack, args.provider)
        gh_path = path / ".github" / "workflows" / "deploy.yml"
        if not args.dry_run:
            gh_path.parent.mkdir(parents=True, exist_ok=True)
            gh_path.write_text(gh, encoding="utf-8")
        files_written[".github/workflows/deploy.yml"] = gh

    if args.gitlab:
        gl = generate_gitlab_ci(stack, args.provider)
        gl_path = path / ".gitlab-ci.yml"
        if not args.dry_run:
            gl_path.write_text(gl, encoding="utf-8")
        files_written[".gitlab-ci.yml"] = gl

    if args.dry_run:
        console.print("[yellow]Dry run — no files written[/yellow]\n")

    print_ci_config(files_written)
    show_success(f"CI/CD config {'previewed' if args.dry_run else 'generated'}")
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

    rollback_p = subparsers.add_parser("rollback", help="Rollback to a snapshot")
    rollback_p.add_argument("snapshot_id", nargs="?", default=None, help="Snapshot ID to restore")
    rollback_p.set_defaults(func=cmd_rollback)

    snapshots_p = subparsers.add_parser("snapshots", help="List deployment snapshots")
    snapshots_p.set_defaults(func=cmd_snapshots)

    secrets_p = subparsers.add_parser("secrets", help="Secrets management")
    secrets_sub = secrets_p.add_subparsers(dest="secrets_command")
    secrets_sub.add_parser("init", help="Initialize secrets management")
    secrets_validate = secrets_sub.add_parser("validate", help="Validate .env file")
    secrets_validate.add_argument("path", nargs="?", default=None, help="Path to .env file")
    secrets_p.set_defaults(func=lambda a: None)

    compare_p = subparsers.add_parser("compare", help="Compare costs across providers")
    compare_p.add_argument("path", nargs="?", default=".", help="Project path")
    compare_p.add_argument("-t", "--tier", default="small", choices=["micro", "small", "medium"])
    compare_p.add_argument("--reserved", action="store_true", help="Show reserved instance pricing")
    compare_p.add_argument("--spot", action="store_true", help="Show spot instance pricing")
    compare_p.set_defaults(func=cmd_compare)

    ci_p = subparsers.add_parser("ci", help="Generate CI/CD configuration")
    ci_p.add_argument("path", nargs="?", default=".", help="Project path")
    ci_p.add_argument("-p", "--provider", default="aws", choices=["aws", "gcp", "azure"])
    ci_p.add_argument("--github", action="store_true", help="Generate GitHub Actions")
    ci_p.add_argument("--gitlab", action="store_true", help="Generate GitLab CI")
    ci_p.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    ci_p.set_defaults(func=cmd_ci)

    args = parser.parse_args()

    if not args.command:
        show_banner()
        parser.print_help()
        return 0

    if args.command == "secrets":
        if args.secrets_command == "init":
            return cmd_secrets_init(args)
        elif args.secrets_command == "validate":
            return cmd_secrets_validate(args)
        else:
            show_banner()
            parser.parse_args(["secrets", "--help"])
            return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
