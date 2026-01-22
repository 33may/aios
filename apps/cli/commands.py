"""
CLI Commands Module

Provides command registration, dispatch, and execution for the Natural Language
Query CLI. Supports slash commands like /help, /tasks, /decisions, /search, etc.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
import logging

from datetime import datetime, timedelta

from apps.cli.config import CLIConfig
from apps.cli.query_engine import QueryEngine
from apps.cli.project_detector import detect_project, detect_project_id, ProjectInfo
from apps.cli import formatters
from apps.backend.integrations.graphiti import queries

logger = logging.getLogger(__name__)


@dataclass
class CommandInfo:
    """
    Metadata about a registered command.

    Attributes:
        name: The command name (without slash prefix)
        handler: The function that handles the command
        description: Short description for help text
        usage: Usage pattern (e.g., "/search <query>")
        aliases: Alternative names for the command
    """
    name: str
    handler: Callable[..., str]
    description: str
    usage: str = ""
    aliases: List[str] = field(default_factory=list)


# Global command registry - maps command names to their handlers
COMMANDS: Dict[str, CommandInfo] = {}


def register_command(
    name: str,
    description: str,
    usage: str = "",
    aliases: Optional[List[str]] = None
) -> Callable:
    """
    Decorator to register a command handler function.

    Args:
        name: The command name (without slash prefix)
        description: Short description for help text
        usage: Usage pattern showing command syntax
        aliases: Alternative names for the command

    Returns:
        Decorator function that registers the handler.

    Example:
        @register_command("help", "Show available commands", "/help [command]")
        def cmd_help(handler, args):
            return "Help text..."
    """
    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        cmd_info = CommandInfo(
            name=name,
            handler=func,
            description=description,
            usage=usage or f"/{name}",
            aliases=aliases or []
        )
        # Register under main name
        COMMANDS[name] = cmd_info
        # Register under aliases
        for alias in (aliases or []):
            COMMANDS[alias] = cmd_info
        logger.debug(f"Registered command: {name}")
        return func
    return decorator


class CommandHandler:
    """
    Handles parsing and execution of CLI commands.

    The CommandHandler manages command dispatch, maintains execution context
    (like current project and configuration), and handles command parsing.

    Attributes:
        config: CLI configuration settings
        query_engine: Engine for executing knowledge graph queries
        project_info: Information about the current project context

    Example:
        >>> handler = CommandHandler()
        >>> result = handler.execute("/help")
        >>> print(result)
        Available commands:
        ...
    """

    def __init__(
        self,
        config: Optional[CLIConfig] = None,
        query_engine: Optional[QueryEngine] = None,
        project_info: Optional[ProjectInfo] = None
    ):
        """
        Initialize the command handler.

        Args:
            config: Optional CLI configuration. If not provided, uses defaults.
            query_engine: Optional query engine. If not provided, creates one.
            project_info: Optional project context. If not provided, auto-detects.
        """
        self.config = config or CLIConfig()
        self.query_engine = query_engine or QueryEngine(config=self.config)
        self._project_info = project_info
        self._auto_detect_project = project_info is None
        logger.info("Initialized CommandHandler")

    @property
    def project_info(self) -> Optional[ProjectInfo]:
        """Get the current project information, auto-detecting if needed."""
        if self._auto_detect_project and self._project_info is None:
            if self.config.auto_detect_project:
                self._project_info = detect_project()
        return self._project_info

    @property
    def project_id(self) -> Optional[str]:
        """Get the current project ID, if available."""
        # Explicit project ID from config takes precedence
        if self.config.project_id:
            return self.config.project_id
        # Otherwise use detected project
        if self.project_info:
            return self.project_info.project_id
        return None

    def is_command(self, text: str) -> bool:
        """
        Check if text is a command (starts with /).

        Args:
            text: The input text to check.

        Returns:
            True if text is a command, False otherwise.
        """
        return text.strip().startswith("/")

    def parse_command(self, text: str) -> tuple[str, str]:
        """
        Parse command text into command name and arguments.

        Args:
            text: The full command string (e.g., "/search why did we choose X")

        Returns:
            Tuple of (command_name, arguments_string).

        Example:
            >>> handler.parse_command("/search why ROS2")
            ('search', 'why ROS2')
        """
        text = text.strip()

        # Remove leading slash
        if text.startswith("/"):
            text = text[1:]

        # Split into command and args
        parts = text.split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        return command, args

    def get_command(self, name: str) -> Optional[CommandInfo]:
        """
        Look up a command by name or alias.

        Args:
            name: The command name to look up.

        Returns:
            CommandInfo if found, None otherwise.
        """
        return COMMANDS.get(name.lower())

    def execute(self, text: str) -> str:
        """
        Execute a command string and return the result.

        Parses the command, looks up the handler, and executes it.
        Returns appropriate error messages for unknown commands.

        Args:
            text: The full command string (e.g., "/help" or "/search query")

        Returns:
            The command output as a string.

        Example:
            >>> result = handler.execute("/help")
            >>> print(result)
        """
        command_name, args = self.parse_command(text)

        if not command_name:
            return "Error: Empty command. Use /help for available commands."

        cmd_info = self.get_command(command_name)

        if cmd_info is None:
            suggestions = self._suggest_commands(command_name)
            msg = f"Unknown command: /{command_name}"
            if suggestions:
                msg += f"\nDid you mean: {', '.join(suggestions)}?"
            msg += "\nUse /help for available commands."
            return msg

        try:
            logger.info(f"Executing command: /{command_name}")
            return cmd_info.handler(self, args)
        except Exception as e:
            logger.error(f"Error executing command /{command_name}: {e}")
            return f"Error executing /{command_name}: {str(e)}"

    def _suggest_commands(self, input_name: str, max_suggestions: int = 3) -> List[str]:
        """
        Suggest similar commands based on input.

        Uses simple prefix matching and edit distance heuristics.

        Args:
            input_name: The command name the user typed.
            max_suggestions: Maximum number of suggestions to return.

        Returns:
            List of suggested command names.
        """
        input_lower = input_name.lower()
        suggestions = []

        # Get unique command names (not aliases pointing to same command)
        unique_commands = set()
        for name, info in COMMANDS.items():
            if name == info.name:  # Only add main names, not aliases
                unique_commands.add(name)

        # Find commands that start with the input
        prefix_matches = [cmd for cmd in unique_commands if cmd.startswith(input_lower)]
        suggestions.extend(prefix_matches)

        # Find commands where input is contained
        if len(suggestions) < max_suggestions:
            contains_matches = [
                cmd for cmd in unique_commands
                if input_lower in cmd and cmd not in suggestions
            ]
            suggestions.extend(contains_matches)

        return suggestions[:max_suggestions]

    def list_commands(self) -> List[CommandInfo]:
        """
        Get a list of all registered commands (excluding aliases).

        Returns:
            List of CommandInfo objects for all registered commands.
        """
        seen = set()
        commands = []
        for name, info in COMMANDS.items():
            if info.name not in seen:
                seen.add(info.name)
                commands.append(info)
        return sorted(commands, key=lambda c: c.name)

    def __repr__(self) -> str:
        """String representation of the handler."""
        project = self.project_id or "none"
        return f"CommandHandler(project={project}, commands={len(COMMANDS)})"


# --- Command implementations ---
# Note: Commands are implemented using the @register_command decorator.
# Each command receives (handler: CommandHandler, args: str) and returns str.


@register_command(
    "help",
    "Show available commands and usage information",
    "/help [command]",
    aliases=["h", "?"]
)
def cmd_help(handler: CommandHandler, args: str) -> str:
    """
    Display help information.

    If a command name is provided, shows detailed help for that command.
    Otherwise, shows a list of all available commands.
    """
    args = args.strip()

    if args:
        # Show help for specific command
        cmd_info = handler.get_command(args)
        if cmd_info:
            lines = [
                f"Command: /{cmd_info.name}",
                f"Usage: {cmd_info.usage}",
                f"Description: {cmd_info.description}",
            ]
            if cmd_info.aliases:
                lines.append(f"Aliases: {', '.join('/' + a for a in cmd_info.aliases)}")
            return "\n".join(lines)
        else:
            return f"Unknown command: /{args}\nUse /help to see available commands."

    # Show all commands
    lines = ["Available commands:", ""]
    for cmd_info in handler.list_commands():
        alias_str = ""
        if cmd_info.aliases:
            alias_str = f" (aliases: {', '.join('/' + a for a in cmd_info.aliases)})"
        lines.append(f"  {cmd_info.usage:<25} - {cmd_info.description}{alias_str}")

    lines.append("")
    lines.append("Use /help <command> for detailed information about a command.")

    return "\n".join(lines)


@register_command(
    "tasks",
    "List tasks from the knowledge graph",
    "/tasks [--all] [--verbose]",
    aliases=["t"]
)
def cmd_tasks(handler: CommandHandler, args: str) -> str:
    """
    List tasks from the knowledge graph.

    By default shows tasks from the current project scope.
    Use --all to show tasks from all projects.
    Use --verbose for detailed task information.
    """
    args_lower = args.lower()
    show_all = "--all" in args_lower or "-a" in args_lower
    verbose = "--verbose" in args_lower or "-v" in args_lower

    try:
        # Determine time range for tasks (default: last 30 days)
        end = datetime.now()
        start = end - timedelta(days=30)

        # Get tasks using the queries module
        tasks = queries.query_temporal_nodes(
            start=start,
            end=end,
            node_type="task",
            client=handler.query_engine._client
        )

        # Filter by project if not showing all and project is detected
        if not show_all and handler.project_id:
            tasks = [
                task for task in tasks
                if task.metadata and task.metadata.get("project_id") == handler.project_id
            ]

        # Format and return results
        output_format = handler.config.output_format
        return formatters.format_tasks(tasks, output_format=output_format, verbose=verbose)

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return f"Error listing tasks: {str(e)}"


@register_command(
    "decisions",
    "List decisions from the knowledge graph",
    "/decisions [--all] [--verbose]",
    aliases=["d"]
)
def cmd_decisions(handler: CommandHandler, args: str) -> str:
    """
    List decisions from the knowledge graph.

    By default shows decisions from the current project scope.
    Use --all to show decisions from all projects.
    Use --verbose for detailed decision information including rationale.
    """
    args_lower = args.lower()
    show_all = "--all" in args_lower or "-a" in args_lower
    verbose = "--verbose" in args_lower or "-v" in args_lower

    try:
        # Determine time range for decisions (default: last 90 days)
        end = datetime.now()
        start = end - timedelta(days=90)

        # Get decisions using the queries module
        decisions = queries.query_temporal_nodes(
            start=start,
            end=end,
            node_type="decision",
            client=handler.query_engine._client
        )

        # Filter by project if not showing all and project is detected
        if not show_all and handler.project_id:
            decisions = [
                decision for decision in decisions
                if decision.metadata and decision.metadata.get("project_id") == handler.project_id
            ]

        # Format and return results
        output_format = handler.config.output_format
        return formatters.format_decisions(decisions, output_format=output_format, verbose=verbose)

    except Exception as e:
        logger.error(f"Error listing decisions: {e}")
        return f"Error listing decisions: {str(e)}"


@register_command(
    "recent",
    "Show recent activity from the knowledge graph",
    "/recent [--limit N] [--verbose]",
    aliases=["r"]
)
def cmd_recent(handler: CommandHandler, args: str) -> str:
    """
    Show recent activity from the knowledge graph.

    Lists recent items of all types (tasks, decisions, sessions, etc.)
    sorted by creation time.

    Options:
        --limit N, -l N: Limit to N items (default: 10)
        --verbose, -v: Show detailed information for each item
    """
    args_lower = args.lower()
    verbose = "--verbose" in args_lower or "-v" in args_lower

    # Parse limit option
    limit = 10  # default
    parts = args.split()
    for i, part in enumerate(parts):
        if part in ("--limit", "-l") and i + 1 < len(parts):
            try:
                limit = int(parts[i + 1])
            except ValueError:
                pass

    try:
        # Determine time range for recent items (default: last 7 days)
        end = datetime.now()
        start = end - timedelta(days=7)

        # Get all recent nodes using the queries module
        items = queries.query_temporal_nodes(
            start=start,
            end=end,
            node_type=None,  # All types
            client=handler.query_engine._client
        )

        # Filter by project if project is detected
        if handler.project_id:
            items = [
                item for item in items
                if item.metadata and item.metadata.get("project_id") == handler.project_id
            ]

        # Apply limit
        items = items[:limit]

        # Format and return results
        output_format = handler.config.output_format
        return formatters.format_recent(items, output_format=output_format, verbose=verbose)

    except Exception as e:
        logger.error(f"Error showing recent activity: {e}")
        return f"Error showing recent activity: {str(e)}"
