"""
Natural Language Query CLI - Main Entry Point

Provides a command-line interface for querying the knowledge base with natural
language. Supports both one-shot queries and quick command shortcuts.

Usage:
    python -m apps.cli.main 'why did we choose ROS2?'
    python -m apps.cli.main tasks
    python -m apps.cli.main --help
"""

import sys
import logging
from typing import Optional

import click

from apps.cli.config import CLIConfig
from apps.cli.commands import CommandHandler, COMMANDS
from apps.cli.project_detector import detect_project, ProjectInfo
from apps.cli.query_engine import QueryEngine

# Configure logging
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the CLI application.

    Args:
        verbose: If True, set logging level to DEBUG.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


@click.group(invoke_without_command=True)
@click.argument("query", nargs=-1, required=False)
@click.option(
    "--project", "-p",
    default=None,
    help="Project ID to scope queries to. Auto-detects if not specified."
)
@click.option(
    "--format", "-f", "output_format",
    type=click.Choice(["text", "json", "table"]),
    default=None,
    help="Output format (text, json, or table)."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output and logging."
)
@click.option(
    "--limit", "-l",
    default=None,
    type=int,
    help="Maximum number of results to return."
)
@click.option(
    "--no-auto-detect",
    is_flag=True,
    default=False,
    help="Disable automatic project detection."
)
@click.version_option(version="0.1.0", prog_name="aios")
@click.pass_context
def cli(
    ctx: click.Context,
    query: tuple,
    project: Optional[str],
    output_format: Optional[str],
    verbose: bool,
    limit: Optional[int],
    no_auto_detect: bool
) -> None:
    """
    Natural Language Query CLI for the AIOS knowledge base.

    Ask questions about your codebase, list tasks, decisions, and more.

    \b
    Examples:
        aios 'why did we choose ROS2?'
        aios tasks
        aios decisions --verbose
        aios search 'authentication' --limit 5
        aios status

    Use 'aios COMMAND --help' for more information on a specific command.
    """
    setup_logging(verbose)

    # Build configuration from CLI options
    config = CLIConfig()

    if project:
        config.project_id = project
    if output_format:
        config.output_format = output_format
    if verbose:
        config.verbose = verbose
    if limit is not None:
        config.default_limit = min(limit, config.max_limit)
    if no_auto_detect:
        config.auto_detect_project = False

    # Store config and handler in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose

    # Create command handler (lazy initialization)
    project_info = None
    if not no_auto_detect and config.auto_detect_project and not project:
        project_info = detect_project()

    handler = CommandHandler(
        config=config,
        project_info=project_info
    )
    ctx.obj["handler"] = handler

    # Handle one-shot query mode or show help
    if ctx.invoked_subcommand is None:
        if query:
            # Check if the first argument is a known subcommand
            first_word = query[0]
            cmd = cli.get_command(ctx, first_word)
            if cmd:
                # Forward to the subcommand with remaining arguments
                args = list(query[1:])

                # Handle --help specially to avoid recursion
                if "--help" in args or "-h" in args:
                    # Create a help context and print help for the subcommand
                    with click.Context(cmd, info_name=first_word, parent=ctx) as help_ctx:
                        click.echo(cmd.get_help(help_ctx))
                    return

                # Create context and invoke the subcommand
                try:
                    with cmd.make_context(first_word, args, parent=ctx) as sub_cmd_ctx:
                        return cmd.invoke(sub_cmd_ctx)
                except click.exceptions.Exit:
                    # Click raised Exit (e.g., for --help), this is normal
                    return
            else:
                # One-shot query mode: aios 'why did we choose X?'
                query_text = " ".join(query)
                result = handler.execute(f"/search {query_text}")
                click.echo(result)
        else:
            # No query provided, show help
            click.echo(ctx.get_help())


@cli.command("query")
@click.argument("question", nargs=-1, required=True)
@click.pass_context
def query_cmd(ctx: click.Context, question: tuple) -> None:
    """
    Ask a natural language question about the knowledge base.

    \b
    Examples:
        aios query why did we choose ROS2
        aios query 'what tasks are blocked?'
    """
    handler: CommandHandler = ctx.obj["handler"]
    query_text = " ".join(question)

    result = handler.execute(f"/search {query_text}")
    click.echo(result)


@cli.command("tasks")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show tasks from all projects.")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed task information.")
@click.pass_context
def tasks_cmd(ctx: click.Context, show_all: bool, verbose: bool) -> None:
    """
    List tasks from the knowledge graph.

    Shows tasks from the current project scope by default.
    """
    handler: CommandHandler = ctx.obj["handler"]

    args = []
    if show_all:
        args.append("--all")
    if verbose:
        args.append("--verbose")

    result = handler.execute(f"/tasks {' '.join(args)}")
    click.echo(result)


@cli.command("decisions")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show decisions from all projects.")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed decision information.")
@click.pass_context
def decisions_cmd(ctx: click.Context, show_all: bool, verbose: bool) -> None:
    """
    List decisions from the knowledge graph.

    Shows decisions from the current project scope by default.
    """
    handler: CommandHandler = ctx.obj["handler"]

    args = []
    if show_all:
        args.append("--all")
    if verbose:
        args.append("--verbose")

    result = handler.execute(f"/decisions {' '.join(args)}")
    click.echo(result)


@cli.command("recent")
@click.option("--limit", "-l", default=10, help="Number of items to show.")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information.")
@click.pass_context
def recent_cmd(ctx: click.Context, limit: int, verbose: bool) -> None:
    """
    Show recent activity from the knowledge graph.

    Lists recent items of all types (tasks, decisions, sessions, etc.)
    sorted by creation time.
    """
    handler: CommandHandler = ctx.obj["handler"]

    args = [f"--limit {limit}"]
    if verbose:
        args.append("--verbose")

    result = handler.execute(f"/recent {' '.join(args)}")
    click.echo(result)


@cli.command("search")
@click.argument("query", nargs=-1, required=True)
@click.option("--limit", "-l", default=None, type=int, help="Maximum number of results.")
@click.option("--all", "-a", "show_all", is_flag=True, help="Search across all projects.")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed result information.")
@click.pass_context
def search_cmd(
    ctx: click.Context,
    query: tuple,
    limit: Optional[int],
    show_all: bool,
    verbose: bool
) -> None:
    """
    Search the knowledge graph with natural language.

    \b
    Examples:
        aios search why did we choose ROS2
        aios search authentication --limit 5
        aios search 'blocked tasks' --verbose
    """
    handler: CommandHandler = ctx.obj["handler"]
    query_text = " ".join(query)

    args = [query_text]
    if limit is not None:
        args.append(f"--limit {limit}")
    if show_all:
        args.append("--all")
    if verbose:
        args.append("--verbose")

    result = handler.execute(f"/search {' '.join(args)}")
    click.echo(result)


@cli.command("status")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed status information.")
@click.pass_context
def status_cmd(ctx: click.Context, verbose: bool) -> None:
    """
    Show CLI status and configuration.

    Displays information about the CLI configuration, project context,
    and connection status to the knowledge graph backend.
    """
    handler: CommandHandler = ctx.obj["handler"]

    args = []
    if verbose:
        args.append("--verbose")

    result = handler.execute(f"/status {' '.join(args)}")
    click.echo(result)


@cli.command("project")
@click.argument("name", required=False)
@click.option("--detect", "-d", is_flag=True, help="Force re-detection of the current project.")
@click.option("--clear", "-c", is_flag=True, help="Clear the current project context.")
@click.pass_context
def project_cmd(
    ctx: click.Context,
    name: Optional[str],
    detect: bool,
    clear: bool
) -> None:
    """
    Show or set the current project context.

    Without arguments, shows the current project information.

    \b
    Examples:
        aios project                  # Show current project
        aios project --detect         # Auto-detect project
        aios project my-project       # Set project by name
        aios project --clear          # Clear project context
    """
    handler: CommandHandler = ctx.obj["handler"]

    if clear:
        result = handler.execute("/project --clear")
    elif detect:
        result = handler.execute("/project --detect")
    elif name:
        result = handler.execute(f"/project {name}")
    else:
        result = handler.execute("/project")

    click.echo(result)


@cli.command("help")
@click.argument("command", required=False)
@click.pass_context
def help_cmd(ctx: click.Context, command: Optional[str]) -> None:
    """
    Show help for a command.

    \b
    Examples:
        aios help           # Show all commands
        aios help search    # Show help for search command
    """
    if command:
        # Try to get help for a specific Click command
        cmd = cli.get_command(ctx, command)
        if cmd:
            with ctx.scope() as scoped_ctx:
                click.echo(cmd.get_help(scoped_ctx))
        else:
            # Fall back to slash command help
            handler: CommandHandler = ctx.obj["handler"]
            result = handler.execute(f"/help {command}")
            click.echo(result)
    else:
        # Show general help
        click.echo(ctx.parent.get_help())


def main() -> None:
    """Main entry point for the CLI application."""
    try:
        cli(obj={})
    except Exception as e:
        logger.error(f"CLI error: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
