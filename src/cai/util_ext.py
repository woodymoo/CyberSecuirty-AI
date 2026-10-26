"""Extended utilities for CAI.

This fork runs permanently in open-source mode. The Alias license check and its
remote key-validation phone-home, the system fingerprinting (MAC / machine-id),
the embedded signature verification, and the private Alias package index have
all been removed. The startup never contacts Alias; updates come from public PyPI.
"""
import os
import subprocess
import sys
from typing import Optional, Dict, Any


def _license_off() -> bool:
    """Always True: this fork never contacts the Alias license server.

    Retained so existing callers keep working. CAI runs in open-source mode and
    update operations target the public PyPI ``cai-framework`` package.
    """
    return True


def _chk() -> bool:
    """License check — always passes.

    The original remote validation (system fingerprint + signed request to the
    Alias API) has been removed, so startup never phones home and is never gated.
    """
    return True


def check_system_dependencies() -> tuple[bool, list[str]]:
    """Check for required system dependencies.
    
    Returns:
        Tuple of (all_ok, missing_dependencies)
    """
    import shutil
    required = ["curl"]
    missing = [cmd for cmd in required if shutil.which(cmd) is None]
    return (len(missing) == 0, missing)


def display_missing_dependencies_error(missing: list[str]) -> None:
    """Display friendly error message for missing dependencies."""
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console(stderr=True)
    deps_list = "\n".join(f"  • {dep}" for dep in missing)
    
    install_hint = ""
    if "curl" in missing:
        install_hint = (
            "\n[yellow]Installation hints:[/yellow]\n"
            "  • Debian/Ubuntu: [cyan]sudo apt-get install curl[/cyan]\n"
            "  • macOS:         [cyan]brew install curl[/cyan]"
        )
    
    console.print(
        Panel(
            f"[bold red]Missing Required System Dependencies[/bold red]\n\n"
            f"The following system commands are required:\n\n"
            f"{deps_list}\n"
            f"{install_hint}",
            title="[red]Dependency Error[/red]",
            border_style="red"
        )
    )


def pip_index_timeout_seconds() -> int:
    """Timeout for ``pip index`` in :func:`check_for_updates` (``CAI_UPDATE_PIP_TIMEOUT``, default 10)."""
    try:
        v = int(os.getenv("CAI_UPDATE_PIP_TIMEOUT", "10"))
    except ValueError:
        return 10
    return max(3, min(v, 120))


def user_env_requests_auto_framework_update() -> bool:
    """Return True only if the user explicitly enabled auto-install via environment.

    ``CAI_AUTO_UPDATE`` must be **present** in :data:`os.environ` (e.g. from ``export`` or
    ``.env`` before process start). If the key is missing, startup always prompts.
    When present, the value must be truthy (``1``, ``true``, ``yes``, ``on``); any other
    value (including empty) is treated as off so accidental ``CAI_AUTO_UPDATE=`` does not
    auto-upgrade.
    """
    if "CAI_AUTO_UPDATE" not in os.environ:
        return False
    return os.getenv("CAI_AUTO_UPDATE", "").strip().lower() in ("1", "true", "yes", "on")


def check_for_updates() -> Optional[Dict[str, Any]]:
    """Check if there's an update available for cai-framework.
    
    Returns:
        Dict with update info if available, None if no update or on error
        {
            "current_version": "x.x.x",
            "latest_version": "y.y.y",
            "update_available": True
        }
    """
    try:
        import importlib.metadata
        import re
        
        # Get current installed version
        try:
            current_version = importlib.metadata.version("cai-framework")
        except importlib.metadata.PackageNotFoundError:
            # Development installation
            return None
            
        # Always check against public PyPI (no ALIAS_API_KEY, no private index).
        pip_args = [
            sys.executable, "-m", "pip", "index", "versions",
            "--no-color",
            "cai-framework",
        ]

        # Use pip index to check for latest version without downloading
        result = subprocess.run(
            pip_args,
            capture_output=True,
            text=True,
            timeout=pip_index_timeout_seconds(),
        )
        
        if result.returncode != 0:
            return None
            
        # Parse output to find available versions
        output = result.stdout
        # Look for version numbers in the output
        version_pattern = r'(\d+\.\d+\.\d+(?:\.\w+)?)'
        versions = re.findall(version_pattern, output)
        
        if not versions:
            return None
            
        # Sort versions and get the latest
        from packaging import version as pkg_version
        sorted_versions = sorted(versions, key=pkg_version.parse, reverse=True)
        latest_version = sorted_versions[0] if sorted_versions else None
        
        if not latest_version:
            return None
            
        # Compare versions
        update_available = pkg_version.parse(latest_version) > pkg_version.parse(current_version)
        return {
            "current_version": current_version,
            "latest_version": latest_version,
            "update_available": update_available,
        }

    except Exception:
        # Silently fail - don't interrupt normal operation
        pass

    return None


def prompt_for_update(update_info: Dict[str, Any]) -> bool:
    """Prompt user to update CAI (Rich chrome matches session banner: CAI green / #004433 / grey)."""
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm
    from rich.table import Table
    from rich.text import Text

    from cai.repl.ui.banner import CAI_GREEN

    _grey_mid = "#888888"
    _grey = "dim white"

    console = Console()

    title = Text()
    title.append(" CAI ", style="bold #0d1117 on #00ff9d")
    title.append(" New version available ", style="bold white on #004433")
    title.append(" ", style="on #004433")

    table = Table(
        show_header=False,
        box=box.SIMPLE_HEAD,
        border_style=_grey_mid,
        padding=(0, 1),
        collapse_padding=True,
    )
    table.add_column(style=_grey, no_wrap=True)
    table.add_column()
    table.add_row(
        "Installed",
        Text(update_info["current_version"], style="italic white"),
    )
    table.add_row(
        "Latest",
        Text(update_info["latest_version"], style=f"bold {CAI_GREEN}"),
    )

    panel = Panel(
        table,
        title=title,
        title_align="left",
        border_style=CAI_GREEN,
        expand=False,
        padding=(0, 1),
        subtitle="[dim white]From public PyPI[/dim white]",
        subtitle_align="left",
    )

    console.print()
    console.print(panel)
    console.print()

    from rich.theme import Theme
    styled_console = Console(theme=Theme({
        "prompt.choices": f"bold {CAI_GREEN}",
        "prompt.default": CAI_GREEN,
    }))
    return Confirm.ask(
        f"[bold {CAI_GREEN}]Update now?[/bold {CAI_GREEN}] [dim white](default: no — explicit yes required)[/dim white]",
        default=False,
        console=styled_console,
    )


def perform_update(api_key: str) -> bool:
    """Perform the pip update for cai-framework.

    Args:
        api_key: Unused. Retained for call-site compatibility; updates always
            come from public PyPI.

    Returns:
        True if update succeeded, False otherwise
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.text import Text

    from cai.repl.ui.banner import CAI_GREEN

    console = Console()

    # Always install from public PyPI (no ALIAS_API_KEY, no private index).
    pip_args = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "cai-framework",
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"[bold {CAI_GREEN}]Updating cai-framework…[/bold {CAI_GREEN}]",
            total=None,
        )

        result = subprocess.run(
            pip_args,
            capture_output=True,
            text=True,
        )

        progress.update(task, completed=True)

    if result.returncode == 0:
        ok_line = Text()
        ok_line.append("✓ ", style=f"bold {CAI_GREEN}")
        ok_line.append("Update completed", style="bold white")
        sub = Text()
        try:
            import importlib.metadata

            installed = importlib.metadata.version("cai-framework")
            sub.append(
                f"Installed cai-framework {installed} (same as cai --version). ",
                style="dim white",
            )
        except Exception:
            pass
        sub.append("Restart CAI to load the new version.", style="italic dim white")
        console.print(
            Panel(
                Text.assemble(ok_line, "\n", sub),
                border_style=CAI_GREEN,
                padding=(0, 1),
                title=Text.assemble(
                    (" CAI ", "bold #0d1117 on #00ff9d"),
                    (" Done ", "bold white on #004433"),
                    (" ", "on #004433"),
                ),
                title_align="left",
            )
        )
        return True

    err = Text()
    err.append("Update failed", style="bold white")
    err.append("\n", "")
    err.append(result.stderr or "(no details)", style="dim white")
    console.print(
        Panel(
            err,
            border_style="red",
            title="[bold white]CAI[/bold white]",
            title_align="left",
        )
    )
    return False
