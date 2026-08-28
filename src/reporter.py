"""Rich table output for pod resource efficiency."""

import shutil
import sys

from rich import box
from rich.console import Console
from rich.table import Table

from .models import ContainerMetrics, PodMetrics
from .units import format_cpu, format_memory

# Use actual terminal width when available; fall back to 160 when piped
_width = shutil.get_terminal_size((160, 24)).columns if sys.stdout.isatty() else 160
console = Console(width=_width)


def _eff_cell(ratio: float | None) -> str:
    if ratio is None:
        return "[dim]—[/dim]"
    pct = ratio * 100
    color = "red" if ratio < 0.2 else ("yellow" if ratio < 0.5 else "green")
    return f"[{color}]{pct:.0f}%[/{color}]"


def _is_flagged(c: ContainerMetrics, threshold: float) -> bool:
    cpu_over = c.cpu_efficiency is not None and c.cpu_efficiency < threshold
    mem_over = c.mem_efficiency is not None and c.mem_efficiency < threshold
    no_requests = c.cpu_request is None and c.mem_request is None
    return cpu_over or mem_over or no_requests


def print_table(results: list[PodMetrics], threshold: float, show_all: bool) -> None:
    table = Table(
        title="Pod Resource Efficiency",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Namespace",  style="dim",  max_width=16, no_wrap=True)
    table.add_column("Pod",                       max_width=38, no_wrap=True, overflow="ellipsis")
    table.add_column("Container",                 max_width=20, no_wrap=True, overflow="ellipsis")
    table.add_column("CPU Req",   justify="right", min_width=7)
    table.add_column("CPU Used",  justify="right", min_width=7)
    table.add_column("CPU Eff",   justify="right", min_width=7)
    table.add_column("Mem Req",   justify="right", min_width=7)
    table.add_column("Mem Used",  justify="right", min_width=7)
    table.add_column("Mem Eff",   justify="right", min_width=7)

    rows: list[tuple[PodMetrics, ContainerMetrics]] = []
    for pod in results:
        for c in pod.containers:
            if show_all or _is_flagged(c, threshold):
                rows.append((pod, c))

    rows.sort(key=lambda r: r[1].worst_efficiency)

    for pod, c in rows:
        table.add_row(
            pod.namespace,
            pod.pod_name,
            c.name,
            format_cpu(c.cpu_request),
            format_cpu(c.cpu_usage),
            _eff_cell(c.cpu_efficiency),
            format_memory(c.mem_request),
            format_memory(c.mem_usage),
            _eff_cell(c.mem_efficiency),
        )

    if not rows:
        pct = f"{threshold * 100:.0f}%"
        console.print(f"[green]✓ No containers below {pct} efficiency threshold.[/green]")
        return

    console.print(table)
    console.print(
        f"\n[dim]Flagged: {len(rows)} containers below {threshold*100:.0f}% threshold  "
        f"(red < 20%, yellow < 50%, green ≥ 50%)[/dim]"
    )


def print_no_metrics_warning() -> None:
    console.print(
        "[yellow]⚠ metrics-server not available — showing requests/limits only, "
        "no live usage data.[/yellow]\n"
        "[dim]  Install: kubectl apply -f "
        "https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml[/dim]\n"
    )
