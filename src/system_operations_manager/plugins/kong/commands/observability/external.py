"""External observability commands for Kong Gateway.

Provides CLI commands for querying external observability backends:
- Prometheus: Historical metrics queries
- Elasticsearch/Loki: Log search
- Jaeger/Zipkin: Distributed trace search
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Annotated

import typer
from rich.panel import Panel

from system_operations_manager.cli.output import Table
from system_operations_manager.integrations.observability import (
    ObservabilityClientError,
)
from system_operations_manager.plugins.kong.commands.observability.base import (
    OutputFormat,
    OutputOption,
    console,
    get_formatter,
)

if TYPE_CHECKING:
    from system_operations_manager.services.observability import (
        LogsManager,
        MetricsManager,
        TracingManager,
    )


def _handle_observability_error(error: ObservabilityClientError) -> None:
    """Handle observability client errors."""
    console.print(f"[red]Error:[/red] {error.message}")
    if error.status_code:
        console.print(f"[dim]Status code: {error.status_code}[/dim]")
    raise typer.Exit(1)


def _parse_duration(duration: str) -> timedelta:
    """Parse a duration string like '1h', '30m', '1d' into timedelta."""
    unit = duration[-1].lower()
    value = int(duration[:-1])

    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    else:
        raise ValueError(f"Invalid duration unit: {unit}")


def register_external_metrics_commands(
    app: typer.Typer,
    get_metrics_manager: Callable[[], MetricsManager | None],
) -> None:
    """Register external Prometheus query commands.

    Args:
        app: Typer app to register commands on.
        get_metrics_manager: Factory function for MetricsManager.
    """
    query_app = typer.Typer(
        name="query",
        help="Query metrics from external Prometheus",
        no_args_is_help=True,
    )

    @query_app.command("exec")
    def query_exec(
        promql: Annotated[str, typer.Argument(help="PromQL query expression")],
        time_range: Annotated[
            str,
            typer.Option("--range", "-r", help="Time range (e.g., '5m', '1h', '1d')"),
        ] = "1h",
        step: Annotated[
            str,
            typer.Option("--step", "-s", help="Query resolution step"),
        ] = "1m",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Execute a custom PromQL query.

        Examples:
            ops kong observability metrics query exec 'rate(kong_http_requests_total[5m])'
            ops kong observability metrics query exec 'kong_upstream_target_health' --range 1h
        """
        manager = get_metrics_manager()
        if manager is None:
            console.print("[yellow]Prometheus is not configured.[/yellow]")
            console.print("Configure it in your kong.yaml under observability.prometheus")
            raise typer.Exit(1)

        try:
            end = datetime.now()
            start = end - _parse_duration(time_range)
            results = manager.query_range(promql, start=start, end=end, step=step)

            if not results:
                console.print("[dim]No results found[/dim]")
                return

            if output == OutputFormat.TABLE:
                table = Table(title=f"Query: {promql[:50]}...")
                table.add_column("Labels", style="cyan")
                table.add_column("Value", style="green")

                for result in results[:20]:
                    metric = result.get("metric", {})
                    values = result.get("values", [])
                    labels = ", ".join(f"{k}={v}" for k, v in metric.items() if k != "__name__")
                    latest = values[-1][1] if values else "-"
                    table.add_row(labels[:60], str(latest))

                console.print(table)
                if len(results) > 20:
                    console.print(f"[dim]... and {len(results) - 20} more[/dim]")
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict({"results": results}, title="Query Results")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @query_app.command("rate")
    def query_rate(
        service: Annotated[
            str | None, typer.Option("--service", "-s", help="Filter by service")
        ] = None,
        route: Annotated[str | None, typer.Option("--route", "-r", help="Filter by route")] = None,
        time_range: Annotated[str, typer.Option("--range", help="Rate calculation window")] = "5m",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show Kong request rate (requests/second).

        Examples:
            ops kong observability metrics query rate
            ops kong observability metrics query rate --service my-api
        """
        manager = get_metrics_manager()
        if manager is None:
            console.print("[yellow]Prometheus is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            results = manager.get_request_rate(service=service, route=route, time_range=time_range)

            if not results:
                console.print("[dim]No request rate data available[/dim]")
                return

            if output == OutputFormat.TABLE:
                table = Table(title="Request Rate")
                table.add_column("Service", style="cyan")
                table.add_column("Route", style="yellow")
                table.add_column("Rate (req/s)", style="green", justify="right")

                for result in results:
                    metric = result.get("metric", {})
                    value = result.get("value", [0, 0])
                    rate = float(value[1]) if len(value) > 1 else 0
                    table.add_row(
                        metric.get("service", "-"),
                        metric.get("route", "-"),
                        f"{rate:.2f}",
                    )

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict({"request_rates": results}, title="Request Rate")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @query_app.command("latency")
    def query_latency(
        service: Annotated[
            str | None, typer.Option("--service", "-s", help="Filter by service")
        ] = None,
        time_range: Annotated[str, typer.Option("--range", help="Calculation window")] = "5m",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show Kong latency percentiles (p50, p90, p99).

        Examples:
            ops kong observability metrics query latency
            ops kong observability metrics query latency --service my-api
        """
        manager = get_metrics_manager()
        if manager is None:
            console.print("[yellow]Prometheus is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            results = manager.get_latency_percentiles(service=service, time_range=time_range)

            if not results or all(not v for v in results.values()):
                console.print("[dim]No latency data available[/dim]")
                return

            if output == OutputFormat.TABLE:
                table = Table(title="Latency Percentiles")
                table.add_column("Percentile", style="cyan")
                table.add_column("Latency (ms)", style="green", justify="right")

                for percentile, data in sorted(results.items()):
                    if data and data[0].get("value"):
                        value = data[0]["value"]
                        latency = float(value[1]) if len(value) > 1 else 0
                        table.add_row(f"p{int(percentile * 100)}", f"{latency:.2f}")

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict({"percentiles": results}, title="Latency Percentiles")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @query_app.command("errors")
    def query_errors(
        service: Annotated[
            str | None, typer.Option("--service", "-s", help="Filter by service")
        ] = None,
        time_range: Annotated[str, typer.Option("--range", help="Calculation window")] = "5m",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show Kong error rate (4xx + 5xx responses).

        Examples:
            ops kong observability metrics query errors
            ops kong observability metrics query errors --service my-api
        """
        manager = get_metrics_manager()
        if manager is None:
            console.print("[yellow]Prometheus is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            results = manager.get_error_rate(service=service, time_range=time_range)

            if not results:
                console.print("[dim]No error rate data available[/dim]")
                return

            if output == OutputFormat.TABLE:
                for result in results:
                    value = result.get("value", [0, 0])
                    error_rate = float(value[1]) if len(value) > 1 else 0
                    error_pct = error_rate * 100

                    color = "green" if error_pct < 1 else "yellow" if error_pct < 5 else "red"
                    console.print(
                        Panel(
                            f"[{color}]{error_pct:.2f}%[/{color}]",
                            title="Error Rate",
                            subtitle=f"Time range: {time_range}",
                        )
                    )
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict({"error_rates": results}, title="Error Rate")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @query_app.command("summary")
    def query_summary(
        service: Annotated[
            str | None, typer.Option("--service", "-s", help="Filter by service")
        ] = None,
        time_range: Annotated[str, typer.Option("--range", help="Calculation window")] = "5m",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show a summary of Kong metrics.

        Examples:
            ops kong observability metrics query summary
            ops kong observability metrics query summary --service my-api
        """
        manager = get_metrics_manager()
        if manager is None:
            console.print("[yellow]Prometheus is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            summary = manager.get_summary(service=service, time_range=time_range)

            if output == OutputFormat.TABLE:
                table = Table(title="Kong Metrics Summary")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                table.add_row(
                    "Request Rate", f"{summary.get('request_rate_per_second', 0):.2f} req/s"
                )

                error_rate = summary.get("error_rate", 0) * 100
                error_color = "green" if error_rate < 1 else "yellow" if error_rate < 5 else "red"
                table.add_row("Error Rate", f"[{error_color}]{error_rate:.2f}%[/{error_color}]")

                latency = summary.get("latency_ms", {})
                if latency:
                    for key, value in latency.items():
                        table.add_row(f"Latency ({key})", f"{value:.2f} ms")

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict(summary, title="Metrics Summary")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    app.add_typer(query_app, name="query")


def register_external_logs_commands(
    app: typer.Typer,
    get_logs_manager: Callable[[], LogsManager | None],
) -> None:
    """Register external log search commands.

    Args:
        app: Typer app to register commands on.
        get_logs_manager: Factory function for LogsManager.
    """
    search_app = typer.Typer(
        name="search",
        help="Search logs from Elasticsearch/Loki",
        no_args_is_help=True,
    )

    @search_app.command("query")
    def search_query(
        query: Annotated[str | None, typer.Argument(help="Search query")] = None,
        service: Annotated[
            str | None, typer.Option("--service", "-s", help="Filter by service")
        ] = None,
        route: Annotated[str | None, typer.Option("--route", "-r", help="Filter by route")] = None,
        status_code: Annotated[
            int | None, typer.Option("--status", help="Filter by status code")
        ] = None,
        time_range: Annotated[str, typer.Option("--range", help="Time range")] = "1h",
        limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 50,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Search Kong access logs.

        Examples:
            ops kong observability logs search query "error"
            ops kong observability logs search query --service my-api
            ops kong observability logs search query --status 500 --range 1d
        """
        manager = get_logs_manager()
        if manager is None:
            console.print("[yellow]Log backend (Elasticsearch/Loki) is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            end = datetime.now()
            start = end - _parse_duration(time_range)

            logs = manager.search_logs(
                query=query,
                service=service,
                route=route,
                status_code=status_code,
                start_time=start,
                end_time=end,
                limit=limit,
            )

            if not logs:
                console.print("[dim]No logs found[/dim]")
                return

            if output == OutputFormat.TABLE:
                table = Table(title=f"Kong Logs ({len(logs)} entries)")
                table.add_column("Time", style="dim")
                table.add_column("Service", style="cyan")
                table.add_column("Status", style="yellow")
                table.add_column("Latency", style="green")
                table.add_column("Path", style="white")

                for log in logs[:limit]:
                    timestamp = log.get("@timestamp", log.get("timestamp", "-"))
                    if isinstance(timestamp, datetime):
                        timestamp = timestamp.strftime("%H:%M:%S")
                    elif isinstance(timestamp, str) and len(timestamp) > 19:
                        timestamp = timestamp[11:19]

                    service_name = log.get("service", {})
                    if isinstance(service_name, dict):
                        service_name = service_name.get("name", "-")

                    response = log.get("response", {})
                    status = response.get("status", log.get("response_status", "-"))
                    status_color = (
                        "green"
                        if str(status).startswith("2")
                        else "yellow"
                        if str(status).startswith("4")
                        else "red"
                    )

                    latencies = log.get("latencies", {})
                    latency = latencies.get("request", log.get("latency", "-"))

                    request = log.get("request", {})
                    path = request.get("uri", log.get("path", "-"))

                    table.add_row(
                        str(timestamp),
                        str(service_name),
                        f"[{status_color}]{status}[/{status_color}]",
                        f"{latency}ms" if latency != "-" else "-",
                        str(path)[:40],
                    )

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict({"logs": logs}, title="Kong Logs")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @search_app.command("errors")
    def search_errors(
        service: Annotated[
            str | None, typer.Option("--service", "-s", help="Filter by service")
        ] = None,
        time_range: Annotated[str, typer.Option("--range", help="Time range")] = "1h",
        limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 50,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show Kong error logs (4xx and 5xx responses).

        Examples:
            ops kong observability logs search errors
            ops kong observability logs search errors --service my-api --range 1d
        """
        manager = get_logs_manager()
        if manager is None:
            console.print("[yellow]Log backend is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            end = datetime.now()
            start = end - _parse_duration(time_range)

            logs = manager.get_error_logs(
                service=service,
                start_time=start,
                end_time=end,
                limit=limit,
            )

            if not logs:
                console.print("[green]No error logs found[/green]")
                return

            if output == OutputFormat.TABLE:
                table = Table(title=f"Kong Error Logs ({len(logs)} entries)")
                table.add_column("Time", style="dim")
                table.add_column("Service", style="cyan")
                table.add_column("Status", style="red")
                table.add_column("Path", style="white")
                table.add_column("Error", style="yellow")

                for log in logs[:limit]:
                    timestamp = log.get("@timestamp", log.get("timestamp", "-"))
                    if isinstance(timestamp, datetime):
                        timestamp = timestamp.strftime("%H:%M:%S")

                    service_name = log.get("service", {})
                    if isinstance(service_name, dict):
                        service_name = service_name.get("name", "-")

                    response = log.get("response", {})
                    status = response.get("status", "-")

                    request = log.get("request", {})
                    path = request.get("uri", "-")

                    error = log.get("error", log.get("message", "-"))

                    table.add_row(
                        str(timestamp)[:8],
                        str(service_name),
                        str(status),
                        str(path)[:30],
                        str(error)[:40],
                    )

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict({"errors": logs}, title="Error Logs")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @search_app.command("summary")
    def search_summary(
        service: Annotated[
            str | None, typer.Option("--service", "-s", help="Filter by service")
        ] = None,
        time_range: Annotated[str, typer.Option("--range", help="Time range")] = "1h",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show log statistics summary.

        Examples:
            ops kong observability logs search summary
            ops kong observability logs search summary --service my-api
        """
        manager = get_logs_manager()
        if manager is None:
            console.print("[yellow]Log backend is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            end = datetime.now()
            start = end - _parse_duration(time_range)

            summary = manager.get_summary(
                service=service,
                start_time=start,
                end_time=end,
            )

            if output == OutputFormat.TABLE:
                console.print(f"[bold]Backend:[/bold] {summary.get('backend', 'unknown')}")
                console.print(f"[bold]Time Range:[/bold] {time_range}")
                console.print()

                table = Table(title="Log Summary")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Total Logs", f"{summary.get('total_logs', 0):,}")
                table.add_row("Error Count", f"{summary.get('error_count', 0):,}")

                console.print(table)

                # Status distribution
                status_dist = summary.get("status_distribution", {})
                if status_dist:
                    status_table = Table(title="Status Distribution")
                    status_table.add_column("Status Code", style="cyan")
                    status_table.add_column("Count", style="green", justify="right")

                    for code, count in sorted(status_dist.items()):
                        color = "green" if code < 400 else "yellow" if code < 500 else "red"
                        status_table.add_row(f"[{color}]{code}[/{color}]", f"{count:,}")

                    console.print(status_table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict(summary, title="Log Summary")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    app.add_typer(search_app, name="search")


def register_external_tracing_commands(
    app: typer.Typer,
    get_tracing_manager: Callable[[], TracingManager | None],
) -> None:
    """Register external tracing commands.

    Args:
        app: Typer app to register commands on.
        get_tracing_manager: Factory function for TracingManager.
    """
    traces_app = typer.Typer(
        name="traces",
        help="Query traces from Jaeger/Zipkin",
        no_args_is_help=True,
    )

    @traces_app.command("find")
    def traces_find(
        route: Annotated[str | None, typer.Option("--route", "-r", help="Filter by route")] = None,
        status_code: Annotated[
            int | None, typer.Option("--status", help="Filter by status code")
        ] = None,
        min_duration: Annotated[
            int | None, typer.Option("--min-duration", help="Min duration in ms")
        ] = None,
        time_range: Annotated[str, typer.Option("--range", help="Time range")] = "1h",
        limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 20,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Find Kong request traces.

        Examples:
            ops kong observability tracing traces find
            ops kong observability tracing traces find --route my-route
            ops kong observability tracing traces find --min-duration 500
        """
        manager = get_tracing_manager()
        if manager is None:
            console.print("[yellow]Tracing backend (Jaeger/Zipkin) is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            end = datetime.now()
            start = end - _parse_duration(time_range)

            traces = manager.find_traces(
                route=route,
                status_code=status_code,
                min_duration_ms=min_duration,
                start_time=start,
                end_time=end,
                limit=limit,
            )

            if not traces:
                console.print("[dim]No traces found[/dim]")
                return

            if output == OutputFormat.TABLE:
                table = Table(title=f"Kong Traces ({len(traces)} found)")
                table.add_column("Trace ID", style="cyan")
                table.add_column("Spans", style="yellow", justify="right")
                table.add_column("Duration", style="green", justify="right")
                table.add_column("Services", style="white")

                for trace in traces[:limit]:
                    trace_id = trace.get("traceID", "-")[:16]
                    spans = trace.get("spans", [])
                    span_count = len(spans)

                    # Calculate duration from spans
                    duration = max((s.get("duration", 0) for s in spans), default=0)
                    duration_ms = duration / 1000 if duration > 1000 else duration

                    # Get unique services
                    processes = trace.get("processes", {})
                    services = list({p.get("serviceName", "") for p in processes.values()})

                    table.add_row(
                        trace_id,
                        str(span_count),
                        f"{duration_ms:.1f}ms",
                        ", ".join(services[:3]),
                    )

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict({"traces": traces}, title="Traces")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @traces_app.command("get")
    def traces_get(
        trace_id: Annotated[str, typer.Argument(help="Trace ID")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Get a specific trace by ID.

        Examples:
            ops kong observability tracing traces get abc123def456
        """
        manager = get_tracing_manager()
        if manager is None:
            console.print("[yellow]Tracing backend is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            trace = manager.get_trace(trace_id)

            if output == OutputFormat.TABLE:
                console.print(f"[bold]Trace ID:[/bold] {trace.get('traceID', trace_id)}")
                console.print()

                spans = trace.get("spans", [])
                table = Table(title=f"Spans ({len(spans)})")
                table.add_column("Operation", style="cyan")
                table.add_column("Service", style="yellow")
                table.add_column("Duration", style="green", justify="right")
                table.add_column("Start", style="dim")

                processes = trace.get("processes", {})

                for span in sorted(spans, key=lambda s: s.get("startTime", 0)):
                    process_id = span.get("processID", "")
                    process = processes.get(process_id, {})
                    service = process.get("serviceName", "-")

                    duration = span.get("duration", 0)
                    duration_ms = duration / 1000 if duration > 1000 else duration

                    table.add_row(
                        span.get("operationName", "-"),
                        service,
                        f"{duration_ms:.2f}ms",
                        str(span.get("startTime", "-"))[:10],
                    )

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict(trace, title=f"Trace {trace_id}")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @traces_app.command("slow")
    def traces_slow(
        threshold: Annotated[
            int, typer.Option("--threshold", "-t", help="Duration threshold in ms")
        ] = 500,
        time_range: Annotated[str, typer.Option("--range", help="Time range")] = "1h",
        limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 20,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Find slow traces above duration threshold.

        Examples:
            ops kong observability tracing traces slow
            ops kong observability tracing traces slow --threshold 1000
        """
        manager = get_tracing_manager()
        if manager is None:
            console.print("[yellow]Tracing backend is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            end = datetime.now()
            start = end - _parse_duration(time_range)

            traces = manager.get_slow_traces(
                threshold_ms=threshold,
                start_time=start,
                end_time=end,
                limit=limit,
            )

            if not traces:
                console.print(f"[green]No traces slower than {threshold}ms found[/green]")
                return

            if output == OutputFormat.TABLE:
                table = Table(title=f"Slow Traces (>{threshold}ms)")
                table.add_column("Trace ID", style="cyan")
                table.add_column("Duration", style="red", justify="right")
                table.add_column("Spans", style="yellow", justify="right")

                for trace in traces[:limit]:
                    trace_id = trace.get("traceID", "-")[:16]
                    spans = trace.get("spans", [])
                    duration = max((s.get("duration", 0) for s in spans), default=0)
                    duration_ms = duration / 1000 if duration > 1000 else duration

                    table.add_row(trace_id, f"{duration_ms:.1f}ms", str(len(spans)))

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict({"slow_traces": traces}, title="Slow Traces")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @traces_app.command("errors")
    def traces_errors(
        time_range: Annotated[str, typer.Option("--range", help="Time range")] = "1h",
        limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 20,
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Find traces with errors.

        Examples:
            ops kong observability tracing traces errors
            ops kong observability tracing traces errors --range 1d
        """
        manager = get_tracing_manager()
        if manager is None:
            console.print("[yellow]Tracing backend is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            end = datetime.now()
            start = end - _parse_duration(time_range)

            traces = manager.get_error_traces(
                start_time=start,
                end_time=end,
                limit=limit,
            )

            if not traces:
                console.print("[green]No error traces found[/green]")
                return

            if output == OutputFormat.TABLE:
                table = Table(title="Error Traces")
                table.add_column("Trace ID", style="cyan")
                table.add_column("Duration", style="yellow", justify="right")
                table.add_column("Error Spans", style="red", justify="right")

                for trace in traces[:limit]:
                    trace_id = trace.get("traceID", "-")[:16]
                    spans = trace.get("spans", [])
                    duration = max((s.get("duration", 0) for s in spans), default=0)
                    duration_ms = duration / 1000 if duration > 1000 else duration

                    # Count error spans
                    error_count = sum(
                        1
                        for s in spans
                        if any(
                            t.get("key") == "error" and t.get("value") for t in s.get("tags", [])
                        )
                    )

                    table.add_row(trace_id, f"{duration_ms:.1f}ms", str(error_count))

                console.print(table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict({"error_traces": traces}, title="Error Traces")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @traces_app.command("analyze")
    def traces_analyze(
        trace_id: Annotated[str, typer.Argument(help="Trace ID to analyze")],
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Analyze a trace for performance insights.

        Examples:
            ops kong observability tracing traces analyze abc123def456
        """
        manager = get_tracing_manager()
        if manager is None:
            console.print("[yellow]Tracing backend is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            analysis = manager.analyze_trace(trace_id)

            if output == OutputFormat.TABLE:
                console.print(
                    f"[bold]Trace Analysis: {analysis.get('trace_id', trace_id)[:16]}[/bold]"
                )
                console.print()

                table = Table(title="Summary")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                duration_us = analysis.get("total_duration_us", 0)
                duration_ms = duration_us / 1000

                table.add_row("Total Duration", f"{duration_ms:.2f}ms")
                table.add_row("Span Count", str(analysis.get("span_count", 0)))

                slowest = analysis.get("slowest_span", {})
                if slowest:
                    slowest_duration = slowest.get("duration_us", 0) / 1000
                    table.add_row(
                        "Slowest Span",
                        f"{slowest.get('operation', slowest.get('name', '-'))} ({slowest_duration:.2f}ms)",
                    )

                console.print(table)

                # Service breakdown
                breakdown = analysis.get("service_breakdown", {})
                if breakdown:
                    breakdown_table = Table(title="Service Breakdown")
                    breakdown_table.add_column("Service", style="cyan")
                    breakdown_table.add_column("Duration", style="green", justify="right")
                    breakdown_table.add_column("% of Total", style="yellow", justify="right")

                    total = sum(breakdown.values())
                    for service, duration in sorted(breakdown.items(), key=lambda x: -x[1]):
                        pct = (duration / total * 100) if total > 0 else 0
                        duration_ms = duration / 1000
                        breakdown_table.add_row(service, f"{duration_ms:.2f}ms", f"{pct:.1f}%")

                    console.print(breakdown_table)
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict(analysis, title="Trace Analysis")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    @traces_app.command("summary")
    def traces_summary(
        time_range: Annotated[str, typer.Option("--range", help="Time range")] = "1h",
        output: OutputOption = OutputFormat.TABLE,
    ) -> None:
        """Show tracing statistics summary.

        Examples:
            ops kong observability tracing traces summary
            ops kong observability tracing traces summary --range 1d
        """
        manager = get_tracing_manager()
        if manager is None:
            console.print("[yellow]Tracing backend is not configured.[/yellow]")
            raise typer.Exit(1)

        try:
            end = datetime.now()
            start = end - _parse_duration(time_range)

            summary = manager.get_summary(start_time=start, end_time=end)

            if output == OutputFormat.TABLE:
                console.print(f"[bold]Backend:[/bold] {summary.get('backend', 'unknown')}")
                console.print(f"[bold]Service:[/bold] {summary.get('service_name', '-')}")
                console.print()

                table = Table(title="Tracing Summary")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Traces Found", str(summary.get("trace_count", 0)))
                table.add_row("Error Traces", str(summary.get("error_trace_count", 0)))

                stats = summary.get("duration_stats", {})
                if stats:
                    table.add_row("Min Duration", f"{stats.get('min_us', 0) / 1000:.2f}ms")
                    table.add_row("Max Duration", f"{stats.get('max_us', 0) / 1000:.2f}ms")
                    table.add_row("Avg Duration", f"{stats.get('avg_us', 0) / 1000:.2f}ms")
                    table.add_row("P50 Duration", f"{stats.get('p50_us', 0) / 1000:.2f}ms")
                    table.add_row("P99 Duration", f"{stats.get('p99_us', 0) / 1000:.2f}ms")

                console.print(table)

                services = summary.get("services", [])
                if services:
                    console.print(f"\n[bold]Traced Services:[/bold] {', '.join(services[:10])}")
            else:
                formatter = get_formatter(output, console)
                formatter.format_dict(summary, title="Tracing Summary")

        except ObservabilityClientError as e:
            _handle_observability_error(e)

    app.add_typer(traces_app, name="traces")
