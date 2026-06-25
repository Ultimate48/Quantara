"""
Rich-based display helpers for Quantara CLI.
Provides colored tables, success/error messages, and formatted output.
Falls back to plain text if rich is not installed.
"""

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Shared console instance
if RICH_AVAILABLE:
    console = Console()
else:
    console = None


def print_success(msg: str):
    if RICH_AVAILABLE:
        console.print(f"[bold green]✓[/bold green] {msg}")
    else:
        print(f"[OK] {msg}")


def print_error(msg: str):
    if RICH_AVAILABLE:
        console.print(f"[bold red]✗[/bold red] {msg}")
    else:
        print(f"[ERROR] {msg}")


def print_warning(msg: str):
    if RICH_AVAILABLE:
        console.print(f"[bold yellow]⚠[/bold yellow] {msg}")
    else:
        print(f"[WARNING] {msg}")


def print_info(msg: str):
    if RICH_AVAILABLE:
        console.print(f"[dim]ℹ[/dim] {msg}")
    else:
        print(f"[INFO] {msg}")


def print_table(title: str, columns: list, rows: list, highlight_first: bool = False):
    """
    Print a formatted table.
    columns: list of (header, justify, style) tuples — style can be None
    rows: list of lists/tuples of string values
    """
    if RICH_AVAILABLE:
        table = Table(title=title, box=box.ROUNDED, show_lines=False,
                      header_style="bold cyan", title_style="bold white")
        for col_name, justify, style in columns:
            table.add_column(col_name, justify=justify, style=style or "")
        for i, row in enumerate(rows):
            style = "bold" if highlight_first and i == 0 else None
            table.add_row(*[str(v) for v in row], style=style)
        console.print(table)
    else:
        # Fallback: plain text table
        widths = []
        headers = [c[0] for c in columns]
        all_rows = [headers] + [[str(v) for v in row] for row in rows]
        for col_idx in range(len(columns)):
            widths.append(max(len(r[col_idx]) for r in all_rows) + 2)

        print(f"\n{title}")
        header_line = "".join(h.ljust(w) for h, w in zip(headers, widths))
        print(header_line)
        print("-" * sum(widths))
        for row in rows:
            print("".join(str(v).ljust(w) for v, w in zip(row, widths)))


def print_metrics(metrics: dict, ticker: str, strategy_name: str,
                  initial_capital: float, final_value: float):
    """Print backtest metrics in a formatted panel."""
    if RICH_AVAILABLE:
        # Color-code return and drawdown
        ret = metrics["total_return"]
        ret_color = "green" if ret >= 0 else "red"
        dd = metrics["max_drawdown"]
        sharpe = metrics["sharpe_ratio"]
        sharpe_color = "green" if sharpe >= 1.0 else "yellow" if sharpe >= 0 else "red"

        content = Text()
        content.append(f"Initial Capital : {initial_capital:>14,.2f}\n")
        content.append(f"Final Value     : {final_value:>14,.2f}\n")
        content.append("Total Return    : ")
        content.append(f"{ret:>13.2f}%\n", style=ret_color)
        content.append("Sharpe Ratio    : ")
        content.append(f"{sharpe:>14.2f}\n", style=sharpe_color)
        content.append("Max Drawdown    : ")
        content.append(f"{dd:>13.2f}%\n", style="red")
        content.append(f"Win Rate        : {metrics['win_rate']:>13.2f}%\n")
        content.append(f"Total Trades    : {metrics['total_trades']:>14}")

        panel = Panel(content, title=f"[bold]{strategy_name}[/bold] on [cyan]{ticker}[/cyan]",
                      border_style="blue", expand=False)
        console.print(panel)
    else:
        print(f"\n{'='*50}")
        print(f"Backtest: {strategy_name} on {ticker}")
        print(f"{'='*50}")
        print(f"Initial Capital : {initial_capital:,.2f}")
        print(f"Final Value     : {final_value:,.2f}")
        print(f"Total Return    : {metrics['total_return']:.2f}%")
        print(f"Sharpe Ratio    : {metrics['sharpe_ratio']:.2f}")
        print(f"Max Drawdown    : {metrics['max_drawdown']:.2f}%")
        print(f"Win Rate        : {metrics['win_rate']:.2f}%")
        print(f"Total Trades    : {metrics['total_trades']}")
        print(f"{'='*50}\n")


def print_strategy_detail(strategy: dict):
    """Print full strategy definition in a formatted way."""
    if RICH_AVAILABLE:
        console.print(f"\n[bold cyan]Strategy:[/bold cyan] {strategy['name']}")
        console.print(f"[dim]Description:[/dim] {strategy['description'] or '—'}")
        console.print(f"[dim]Created:[/dim]     {strategy['created_at']}")
        console.print()

        table = Table(title="Columns", box=box.SIMPLE, header_style="bold")
        table.add_column("Name", style="cyan")
        table.add_column("Formula", style="white")
        for col in strategy["columns"]:
            table.add_row(col["name"], col["formula"])
        console.print(table)

        console.print(f"\n[bold]Signal Rule:[/bold]\n  [yellow]{strategy['signal_rule']}[/yellow]\n")
    else:
        print(f"\nName        : {strategy['name']}")
        print(f"Description : {strategy['description']}")
        print(f"Created     : {strategy['created_at']}")
        print(f"\nColumns:")
        for col in strategy["columns"]:
            print(f"  {col['name']} = {col['formula']}")
        print(f"\nSignal Rule:\n  {strategy['signal_rule']}")


def print_comparison(results: list, ticker: str):
    """Print a side-by-side strategy comparison table."""
    if not results:
        return

    if RICH_AVAILABLE:
        table = Table(title=f"Strategy Comparison on {ticker}", box=box.ROUNDED,
                      header_style="bold cyan", title_style="bold white")
        table.add_column("Metric", style="bold", justify="left")
        for r in results:
            table.add_column(r["name"], justify="right")

        metric_rows = [
            ("Initial Capital", lambda r: f"{r['initial_capital']:,.0f}"),
            ("Final Value", lambda r: f"{r['final_value']:,.0f}"),
            ("Total Return", lambda r: f"{r['metrics']['total_return']:.2f}%"),
            ("Sharpe Ratio", lambda r: f"{r['metrics']['sharpe_ratio']:.2f}"),
            ("Max Drawdown", lambda r: f"{r['metrics']['max_drawdown']:.2f}%"),
            ("Win Rate", lambda r: f"{r['metrics']['win_rate']:.2f}%"),
            ("Total Trades", lambda r: f"{r['metrics']['total_trades']}"),
        ]

        for label, getter in metric_rows:
            row = [label] + [getter(r) for r in results]
            table.add_row(*row)

        console.print(table)
    else:
        # Fallback to plain text comparison
        from backtest.engine import compare_backtests
        compare_backtests(results, ticker)


def print_indicators(indicators: list):
    """Print available indicator presets."""
    if RICH_AVAILABLE:
        table = Table(title="Available Indicator Presets", box=box.ROUNDED,
                      header_style="bold cyan")
        table.add_column("Name", style="cyan bold")
        table.add_column("Usage", style="yellow")
        table.add_column("Description", style="white")
        for ind in indicators:
            table.add_row(ind["name"], f"--indicator {ind['usage']}", ind["description"])
        console.print(table)
    else:
        print("\nAvailable Indicator Presets:")
        print("-" * 60)
        for ind in indicators:
            print(f"  {ind['name']:<8} --indicator {ind['usage']:<20} {ind['description']}")
