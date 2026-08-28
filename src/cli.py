import argparse
import sys

import urllib3

from .collector import collect
from .reporter import console, print_no_metrics_warning, print_table


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="k8s-resource-advisor",
        description="Find over-provisioned pods in your Kubernetes cluster.",
    )
    parser.add_argument(
        "-n", "--namespace",
        metavar="NAMESPACE",
        help="Namespace to scan (default: all namespaces)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        metavar="RATIO",
        help="Flag containers below this efficiency ratio (default: 0.30 = 30%%)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="show_all",
        help="Show all containers, not just flagged ones",
    )
    args = parser.parse_args()

    scope = f"namespace: {args.namespace}" if args.namespace else "all namespaces"
    console.print(f"[bold]Scanning {scope}...[/bold]")

    try:
        results, metrics_available = collect(namespace=args.namespace)
    except urllib3.exceptions.MaxRetryError:
        console.print("[red]Error: cannot reach the API server.[/red]")
        console.print("[dim]Check: kubectl get pods works? AWS SSO session active?[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    total_containers = sum(len(p.containers) for p in results)
    console.print(
        f"Found [bold]{total_containers}[/bold] containers across "
        f"[bold]{len(results)}[/bold] running pods\n"
    )

    if not metrics_available:
        print_no_metrics_warning()

    print_table(results, threshold=args.threshold, show_all=args.show_all)
