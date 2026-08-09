"""Rich terminal display for Forge."""

from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box

console = Console()


def show_banner():
    """Show the Forge banner."""
    banner = Text()
    banner.append("⚡ Forge", style="bold cyan")
    banner.append(" — Universal Deploy Engine\n", style="dim")
    banner.append("    Deploy any stack to any cloud", style="dim")
    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))


def show_stack(stack):
    """Show detected stack info."""
    table = Table(
        title="Detected Stack",
        box=box.ROUNDED,
        title_style="bold cyan",
        border_style="cyan",
        padding=(0, 1),
    )
    table.add_column("Property", style="bold")
    table.add_column("Value")

    table.add_row("Path", str(stack.path))
    table.add_row("Language", stack.primary_language or "Unknown")
    table.add_row("Framework", stack.primary_framework or "None detected")
    table.add_row("Services", ", ".join(stack.services) or "None")
    table.add_row("Docker", "✓" if stack.has_docker else "✗")
    table.add_row("Terraform", "✓" if stack.has_terraform else "✗")
    table.add_row("Port", str(stack.port) if stack.port else "auto")

    console.print(table)


def show_providers(providers: list[dict]):
    """Show available cloud providers."""
    table = Table(
        title="Cloud Providers",
        box=box.ROUNDED,
        title_style="bold green",
        border_style="green",
        padding=(0, 1),
    )
    table.add_column("Provider", style="bold")
    table.add_column("Status")
    table.add_column("Account")

    for p in providers:
        status = "[green]✓ Ready[/green]" if p["available"] else "[red]✗ Not configured[/red]"
        account = p["account"] or "—"
        table.add_row(p["label"], status, account)

    console.print(table)


def show_preview(preview: dict):
    """Show deployment preview."""
    lines = []
    lines.append(f"[bold cyan]Project:[/bold cyan]   {preview['project']}")
    lines.append(f"[bold cyan]Stack:[/bold cyan]     {preview['stack']}")
    lines.append(f"[bold cyan]Provider:[/bold cyan]  {preview['provider'].upper()}")
    lines.append(f"[bold cyan]Port:[/bold cyan]      {preview['port'] or 'auto-detect'}")

    if preview["services"]:
        lines.append(f"[bold cyan]Services:[/bold cyan]  {', '.join(preview['services'])}")

    if preview["files_to_generate"]:
        lines.append("")
        lines.append("[bold yellow]Files to generate:[/bold yellow]")
        for f in preview["files_to_generate"]:
            lines.append(f"  [green]+[/green] {f}")

    if preview["resources"]:
        lines.append("")
        lines.append("[bold yellow]Cloud resources:[/bold yellow]")
        for r in preview["resources"]:
            lines.append(f"  [blue]~[/blue] {r}")

    console.print(Panel("\n".join(lines), title="Deployment Preview", border_style="yellow", padding=(1, 2)))


def show_cost(est):
    """Show cost estimate."""
    table = Table(
        title="Monthly Cost Estimate",
        box=box.ROUNDED,
        title_style="bold magenta",
        border_style="magenta",
        padding=(0, 1),
    )
    table.add_column("Component", style="bold")
    table.add_column("Cost", justify="right")

    table.add_row("Compute", f"${est.compute:.2f}")
    table.add_row("Database", f"${est.database:.2f}")
    table.add_row("Cache", f"${est.cache:.2f}")
    table.add_row("Storage", f"${est.storage:.2f}")
    table.add_row("Networking", f"${est.networking:.2f}")
    table.add_row("[bold]Total[/bold]", f"[bold]${est.total:.2f}[/bold]")

    console.print(table)


def show_generated_files(files: dict[str, str]):
    """Show generated file contents."""
    for filename, content in files.items():
        console.print(f"\n[bold green]📄 {filename}[/bold green]")
        console.print("─" * 60)
        console.print(content, highlight=True)


def show_deploy_result(success: bool, message: str):
    """Show deployment result."""
    if success:
        console.print(Panel(
            f"[green]✓ {message}[/green]",
            title="Deploy Complete",
            border_style="green",
            padding=(0, 2),
        ))
    else:
        console.print(Panel(
            f"[red]✗ {message}[/red]",
            title="Deploy Failed",
            border_style="red",
            padding=(0, 2),
        ))


def show_error(message: str):
    """Show an error message."""
    console.print(f"[red]✗ Error:[/red] {message}")


def show_warning(message: str):
    """Show a warning message."""
    console.print(f"[yellow]⚠ Warning:[/yellow] {message}")


def show_success(message: str):
    """Show a success message."""
    console.print(f"[green]✓[/green] {message}")
