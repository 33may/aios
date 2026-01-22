"""
Tests for CLI Commands Module

Tests command registration, dispatch, execution, and all individual command
implementations (/help, /tasks, /decisions, /search, /project, /status, /recent).
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from apps.cli.commands import (
    CommandInfo,
    CommandHandler,
    COMMANDS,
    register_command,
    cmd_help,
    cmd_tasks,
    cmd_decisions,
    cmd_search,
    cmd_project,
    cmd_status,
    cmd_recent,
)
from apps.cli.config import CLIConfig
from apps.cli.query_engine import QueryEngine
from apps.cli.project_detector import ProjectInfo
from apps.backend.integrations.graphiti.models import Node


# --- CommandInfo Dataclass Tests ---


class TestCommandInfo:
    """Tests for CommandInfo dataclass."""

    def test_command_info_basic_creation(self):
        """Test basic CommandInfo creation with required fields."""

        def dummy_handler(handler, args):
            return "test"

        info = CommandInfo(
            name="test",
            handler=dummy_handler,
            description="Test command"
        )

        assert info.name == "test"
        assert info.handler == dummy_handler
        assert info.description == "Test command"

    def test_command_info_with_usage(self):
        """Test CommandInfo with usage field."""

        def dummy_handler(handler, args):
            return "test"

        info = CommandInfo(
            name="test",
            handler=dummy_handler,
            description="Test command",
            usage="/test <arg>"
        )

        assert info.usage == "/test <arg>"

    def test_command_info_with_aliases(self):
        """Test CommandInfo with aliases field."""

        def dummy_handler(handler, args):
            return "test"

        info = CommandInfo(
            name="test",
            handler=dummy_handler,
            description="Test command",
            aliases=["t", "tst"]
        )

        assert info.aliases == ["t", "tst"]

    def test_command_info_default_values(self):
        """Test CommandInfo default values."""

        def dummy_handler(handler, args):
            return "test"

        info = CommandInfo(
            name="test",
            handler=dummy_handler,
            description="Test command"
        )

        assert info.usage == ""
        assert info.aliases == []


# --- COMMANDS Registry Tests ---


class TestCommandsRegistry:
    """Tests for COMMANDS registry."""

    def test_commands_is_dict(self):
        """Test that COMMANDS is a dictionary."""
        assert isinstance(COMMANDS, dict)

    def test_commands_contains_help(self):
        """Test that COMMANDS contains help command."""
        assert "help" in COMMANDS
        assert isinstance(COMMANDS["help"], CommandInfo)

    def test_commands_contains_tasks(self):
        """Test that COMMANDS contains tasks command."""
        assert "tasks" in COMMANDS
        assert isinstance(COMMANDS["tasks"], CommandInfo)

    def test_commands_contains_decisions(self):
        """Test that COMMANDS contains decisions command."""
        assert "decisions" in COMMANDS
        assert isinstance(COMMANDS["decisions"], CommandInfo)

    def test_commands_contains_search(self):
        """Test that COMMANDS contains search command."""
        assert "search" in COMMANDS
        assert isinstance(COMMANDS["search"], CommandInfo)

    def test_commands_contains_project(self):
        """Test that COMMANDS contains project command."""
        assert "project" in COMMANDS
        assert isinstance(COMMANDS["project"], CommandInfo)

    def test_commands_contains_status(self):
        """Test that COMMANDS contains status command."""
        assert "status" in COMMANDS
        assert isinstance(COMMANDS["status"], CommandInfo)

    def test_commands_contains_recent(self):
        """Test that COMMANDS contains recent command."""
        assert "recent" in COMMANDS
        assert isinstance(COMMANDS["recent"], CommandInfo)

    def test_commands_aliases_registered(self):
        """Test that command aliases are registered."""
        # Help aliases
        assert "h" in COMMANDS
        assert "?" in COMMANDS

        # Tasks alias
        assert "t" in COMMANDS

        # Decisions alias
        assert "d" in COMMANDS

        # Search aliases
        assert "s" in COMMANDS
        assert "find" in COMMANDS

        # Project aliases
        assert "proj" in COMMANDS
        assert "p" in COMMANDS

        # Status alias
        assert "stat" in COMMANDS

        # Recent alias
        assert "r" in COMMANDS

    def test_aliases_point_to_same_command_info(self):
        """Test that aliases point to the same CommandInfo as main name."""
        assert COMMANDS["h"] is COMMANDS["help"]
        assert COMMANDS["?"] is COMMANDS["help"]
        assert COMMANDS["t"] is COMMANDS["tasks"]
        assert COMMANDS["d"] is COMMANDS["decisions"]
        assert COMMANDS["s"] is COMMANDS["search"]
        assert COMMANDS["find"] is COMMANDS["search"]


# --- Register Command Decorator Tests ---


class TestRegisterCommand:
    """Tests for register_command decorator."""

    def test_register_command_adds_to_registry(self):
        """Test that register_command adds command to registry."""
        # Store original state
        original_count = len(COMMANDS)

        @register_command(
            "test_cmd_1",
            "Test command 1",
            "/test_cmd_1"
        )
        def test_handler_1(handler, args):
            return "test"

        # Verify command was added
        assert "test_cmd_1" in COMMANDS
        assert COMMANDS["test_cmd_1"].name == "test_cmd_1"

        # Clean up
        del COMMANDS["test_cmd_1"]

    def test_register_command_with_aliases(self):
        """Test that register_command registers aliases."""

        @register_command(
            "test_cmd_2",
            "Test command 2",
            "/test_cmd_2",
            aliases=["tc2", "test2"]
        )
        def test_handler_2(handler, args):
            return "test"

        # Verify aliases were registered
        assert "test_cmd_2" in COMMANDS
        assert "tc2" in COMMANDS
        assert "test2" in COMMANDS
        assert COMMANDS["tc2"] is COMMANDS["test_cmd_2"]
        assert COMMANDS["test2"] is COMMANDS["test_cmd_2"]

        # Clean up
        del COMMANDS["test_cmd_2"]
        del COMMANDS["tc2"]
        del COMMANDS["test2"]

    def test_register_command_returns_function(self):
        """Test that register_command returns the original function."""

        @register_command(
            "test_cmd_3",
            "Test command 3"
        )
        def test_handler_3(handler, args):
            return "result"

        # Function should still be callable
        mock_handler = Mock()
        result = test_handler_3(mock_handler, "args")
        assert result == "result"

        # Clean up
        del COMMANDS["test_cmd_3"]

    def test_register_command_sets_default_usage(self):
        """Test that register_command sets default usage when not provided."""

        @register_command(
            "test_cmd_4",
            "Test command 4"
        )
        def test_handler_4(handler, args):
            return "test"

        assert COMMANDS["test_cmd_4"].usage == "/test_cmd_4"

        # Clean up
        del COMMANDS["test_cmd_4"]


# --- CommandHandler Initialization Tests ---


class TestCommandHandlerInit:
    """Tests for CommandHandler initialization."""

    def test_init_default_config(self):
        """Test that CommandHandler initializes with default config."""
        handler = CommandHandler()

        assert handler.config is not None
        assert isinstance(handler.config, CLIConfig)

    def test_init_custom_config(self):
        """Test that CommandHandler accepts custom config."""
        config = CLIConfig(default_limit=5, output_format="json")
        handler = CommandHandler(config=config)

        assert handler.config.default_limit == 5
        assert handler.config.output_format == "json"

    def test_init_creates_query_engine(self):
        """Test that CommandHandler creates query engine."""
        handler = CommandHandler()

        assert handler.query_engine is not None
        assert isinstance(handler.query_engine, QueryEngine)

    def test_init_custom_query_engine(self):
        """Test that CommandHandler accepts custom query engine."""
        engine = QueryEngine()
        handler = CommandHandler(query_engine=engine)

        assert handler.query_engine is engine

    def test_init_project_info_none_by_default(self):
        """Test that project_info is None by default (before auto-detection)."""
        handler = CommandHandler()

        # Without calling project_info property, _project_info should be None
        assert handler._project_info is None

    def test_init_custom_project_info(self):
        """Test that CommandHandler accepts custom project info."""
        project_info = ProjectInfo(
            name="test-project",
            path="/test/path",
            project_id="proj-123",
            has_git=True,
            has_aios=False
        )
        handler = CommandHandler(project_info=project_info)

        assert handler._project_info is project_info
        assert handler._project_info.name == "test-project"


# --- CommandHandler Property Tests ---


class TestCommandHandlerProperties:
    """Tests for CommandHandler properties."""

    def test_project_id_from_config(self):
        """Test that project_id uses config.project_id when set."""
        config = CLIConfig(project_id="config-proj-id")
        handler = CommandHandler(config=config)

        assert handler.project_id == "config-proj-id"

    def test_project_id_from_project_info(self):
        """Test that project_id uses project_info when config.project_id is not set."""
        project_info = ProjectInfo(
            name="test",
            path="/test",
            project_id="info-proj-id",
            has_git=True,
            has_aios=False
        )
        handler = CommandHandler(project_info=project_info)

        assert handler.project_id == "info-proj-id"

    def test_project_id_config_takes_precedence(self):
        """Test that config.project_id takes precedence over project_info."""
        config = CLIConfig(project_id="config-proj-id")
        project_info = ProjectInfo(
            name="test",
            path="/test",
            project_id="info-proj-id",
            has_git=True,
            has_aios=False
        )
        handler = CommandHandler(config=config, project_info=project_info)

        assert handler.project_id == "config-proj-id"

    def test_project_id_none_when_nothing_set(self):
        """Test that project_id is None when nothing is set."""
        config = CLIConfig(auto_detect_project=False)
        handler = CommandHandler(config=config)

        # Disable auto-detection
        handler._auto_detect_project = False

        assert handler.project_id is None


# --- CommandHandler Method Tests ---


class TestCommandHandlerIsCommand:
    """Tests for CommandHandler.is_command()."""

    def test_is_command_with_slash(self):
        """Test that strings starting with / are commands."""
        handler = CommandHandler()

        assert handler.is_command("/help") is True
        assert handler.is_command("/search test") is True

    def test_is_command_without_slash(self):
        """Test that strings not starting with / are not commands."""
        handler = CommandHandler()

        assert handler.is_command("help") is False
        assert handler.is_command("search test") is False

    def test_is_command_with_whitespace(self):
        """Test that whitespace is handled correctly."""
        handler = CommandHandler()

        assert handler.is_command("  /help") is True
        assert handler.is_command("/help  ") is True
        assert handler.is_command("  /help  ") is True

    def test_is_command_empty_string(self):
        """Test that empty string is not a command."""
        handler = CommandHandler()

        assert handler.is_command("") is False
        assert handler.is_command("   ") is False


class TestCommandHandlerParseCommand:
    """Tests for CommandHandler.parse_command()."""

    def test_parse_command_simple(self):
        """Test parsing simple command."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("/help")

        assert cmd == "help"
        assert args == ""

    def test_parse_command_with_args(self):
        """Test parsing command with arguments."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("/search why did we choose ROS2")

        assert cmd == "search"
        assert args == "why did we choose ROS2"

    def test_parse_command_lowercase(self):
        """Test that command name is lowercased."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("/HELP")

        assert cmd == "help"

    def test_parse_command_with_whitespace(self):
        """Test parsing command with leading/trailing whitespace."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("  /search test  ")

        assert cmd == "search"
        assert args == "test"

    def test_parse_command_without_slash(self):
        """Test parsing text without slash prefix."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("search test")

        assert cmd == "search"
        assert args == "test"

    def test_parse_command_empty(self):
        """Test parsing empty string."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("")

        assert cmd == ""
        assert args == ""

    def test_parse_command_only_slash(self):
        """Test parsing only slash."""
        handler = CommandHandler()

        cmd, args = handler.parse_command("/")

        assert cmd == ""
        assert args == ""


class TestCommandHandlerGetCommand:
    """Tests for CommandHandler.get_command()."""

    def test_get_command_existing(self):
        """Test getting an existing command."""
        handler = CommandHandler()

        cmd_info = handler.get_command("help")

        assert cmd_info is not None
        assert cmd_info.name == "help"

    def test_get_command_by_alias(self):
        """Test getting command by alias."""
        handler = CommandHandler()

        cmd_info = handler.get_command("h")

        assert cmd_info is not None
        assert cmd_info.name == "help"

    def test_get_command_case_insensitive(self):
        """Test that get_command is case insensitive."""
        handler = CommandHandler()

        cmd_info = handler.get_command("HELP")

        assert cmd_info is not None
        assert cmd_info.name == "help"

    def test_get_command_nonexistent(self):
        """Test getting non-existent command returns None."""
        handler = CommandHandler()

        cmd_info = handler.get_command("nonexistent")

        assert cmd_info is None


class TestCommandHandlerExecute:
    """Tests for CommandHandler.execute()."""

    def test_execute_help_command(self):
        """Test executing help command."""
        handler = CommandHandler()

        result = handler.execute("/help")

        assert isinstance(result, str)
        assert "Available commands" in result

    def test_execute_empty_command(self):
        """Test executing empty command."""
        handler = CommandHandler()

        result = handler.execute("/")

        assert "Error" in result
        assert "Empty command" in result

    def test_execute_unknown_command(self):
        """Test executing unknown command."""
        handler = CommandHandler()

        result = handler.execute("/nonexistent")

        assert "Unknown command" in result
        assert "nonexistent" in result

    def test_execute_unknown_command_with_suggestion(self):
        """Test that unknown command provides suggestions."""
        handler = CommandHandler()

        result = handler.execute("/hel")

        assert "Unknown command" in result
        # Should suggest "help"
        assert "Did you mean" in result or "/help" in result

    def test_execute_with_alias(self):
        """Test executing command via alias."""
        handler = CommandHandler()

        result = handler.execute("/h")

        assert "Available commands" in result


class TestCommandHandlerSuggestCommands:
    """Tests for CommandHandler._suggest_commands()."""

    def test_suggest_commands_prefix_match(self):
        """Test that prefix matches are suggested."""
        handler = CommandHandler()

        suggestions = handler._suggest_commands("hel")

        assert "help" in suggestions

    def test_suggest_commands_contains_match(self):
        """Test that contains matches are suggested."""
        handler = CommandHandler()

        suggestions = handler._suggest_commands("ask")

        assert "tasks" in suggestions

    def test_suggest_commands_max_suggestions(self):
        """Test that max_suggestions is respected."""
        handler = CommandHandler()

        suggestions = handler._suggest_commands("", max_suggestions=2)

        assert len(suggestions) <= 2

    def test_suggest_commands_no_duplicates(self):
        """Test that suggestions don't include duplicates."""
        handler = CommandHandler()

        suggestions = handler._suggest_commands("s")

        assert len(suggestions) == len(set(suggestions))


class TestCommandHandlerListCommands:
    """Tests for CommandHandler.list_commands()."""

    def test_list_commands_returns_list(self):
        """Test that list_commands returns a list."""
        handler = CommandHandler()

        commands = handler.list_commands()

        assert isinstance(commands, list)

    def test_list_commands_returns_command_info(self):
        """Test that list_commands returns CommandInfo objects."""
        handler = CommandHandler()

        commands = handler.list_commands()

        assert all(isinstance(cmd, CommandInfo) for cmd in commands)

    def test_list_commands_excludes_aliases(self):
        """Test that list_commands excludes aliases."""
        handler = CommandHandler()

        commands = handler.list_commands()
        names = [cmd.name for cmd in commands]

        # Should have unique names (no aliases)
        assert len(names) == len(set(names))

    def test_list_commands_sorted(self):
        """Test that list_commands returns sorted list."""
        handler = CommandHandler()

        commands = handler.list_commands()
        names = [cmd.name for cmd in commands]

        assert names == sorted(names)


class TestCommandHandlerRepr:
    """Tests for CommandHandler.__repr__()."""

    def test_repr_basic(self):
        """Test basic string representation."""
        handler = CommandHandler()

        repr_str = repr(handler)

        assert "CommandHandler" in repr_str

    def test_repr_includes_project(self):
        """Test that repr includes project info."""
        project_info = ProjectInfo(
            name="test",
            path="/test",
            project_id="proj-123",
            has_git=True,
            has_aios=False
        )
        handler = CommandHandler(project_info=project_info)

        repr_str = repr(handler)

        assert "project=" in repr_str

    def test_repr_includes_command_count(self):
        """Test that repr includes command count."""
        handler = CommandHandler()

        repr_str = repr(handler)

        assert "commands=" in repr_str


# --- Help Command Tests ---


class TestCmdHelp:
    """Tests for /help command."""

    def test_help_lists_all_commands(self):
        """Test that /help lists all commands."""
        handler = CommandHandler()

        result = handler.execute("/help")

        assert "Available commands" in result
        assert "/help" in result
        assert "/tasks" in result
        assert "/decisions" in result
        assert "/search" in result
        assert "/project" in result
        assert "/status" in result
        assert "/recent" in result

    def test_help_shows_descriptions(self):
        """Test that /help shows command descriptions."""
        handler = CommandHandler()

        result = handler.execute("/help")

        # Should have descriptions
        assert "Show available commands" in result

    def test_help_shows_aliases(self):
        """Test that /help shows aliases."""
        handler = CommandHandler()

        result = handler.execute("/help")

        assert "aliases:" in result

    def test_help_specific_command(self):
        """Test that /help <command> shows detailed help."""
        handler = CommandHandler()

        result = handler.execute("/help search")

        assert "Command: /search" in result
        assert "Usage:" in result
        assert "Description:" in result

    def test_help_unknown_command(self):
        """Test that /help <unknown> shows error."""
        handler = CommandHandler()

        result = handler.execute("/help nonexistent")

        assert "Unknown command" in result
        assert "nonexistent" in result


# --- Tasks Command Tests ---


class TestCmdTasks:
    """Tests for /tasks command."""

    def test_tasks_returns_string(self):
        """Test that /tasks returns a string."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/tasks")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_tasks_with_all_flag(self):
        """Test that /tasks --all works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/tasks --all")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_tasks_with_verbose_flag(self):
        """Test that /tasks --verbose works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        # Add a task to test verbose output
        task = Node(type="task", content="Test task", metadata={"status": "pending"})
        handler.query_engine._client.add_node(task)

        result = handler.execute("/tasks --verbose")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_tasks_alias_t(self):
        """Test that /t alias works for tasks."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/t")

        assert isinstance(result, str)

        handler.query_engine.disconnect()


# --- Decisions Command Tests ---


class TestCmdDecisions:
    """Tests for /decisions command."""

    def test_decisions_returns_string(self):
        """Test that /decisions returns a string."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/decisions")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_decisions_with_all_flag(self):
        """Test that /decisions --all works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/decisions --all")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_decisions_with_verbose_flag(self):
        """Test that /decisions --verbose works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/decisions --verbose")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_decisions_alias_d(self):
        """Test that /d alias works for decisions."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/d")

        assert isinstance(result, str)

        handler.query_engine.disconnect()


# --- Search Command Tests ---


class TestCmdSearch:
    """Tests for /search command."""

    def test_search_returns_string(self):
        """Test that /search returns a string."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/search test query")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_search_without_query(self):
        """Test that /search without query shows error."""
        handler = CommandHandler()

        result = handler.execute("/search")

        assert "Error" in result
        assert "query" in result.lower()

    def test_search_with_limit(self):
        """Test that /search --limit N works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/search test --limit 5")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_search_with_limit_short(self):
        """Test that /search -l N works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/search test -l 5")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_search_with_verbose(self):
        """Test that /search --verbose works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        # Add a node for search results
        node = Node(
            type="task",
            content="Test content for search",
            embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
        )
        handler.query_engine._client.add_node(node)

        result = handler.execute("/search test --verbose")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_search_with_all_flag(self):
        """Test that /search --all ignores project scope."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/search test --all")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_search_alias_s(self):
        """Test that /s alias works for search."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/s test")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_search_alias_find(self):
        """Test that /find alias works for search."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/find test")

        assert isinstance(result, str)

        handler.query_engine.disconnect()


# --- Project Command Tests ---


class TestCmdProject:
    """Tests for /project command."""

    def test_project_shows_current(self):
        """Test that /project shows current project."""
        project_info = ProjectInfo(
            name="test-project",
            path="/test/path",
            project_id="proj-123",
            has_git=True,
            has_aios=False
        )
        handler = CommandHandler(project_info=project_info)

        result = handler.execute("/project")

        assert "project" in result.lower()

    def test_project_clear(self):
        """Test that /project --clear clears context."""
        project_info = ProjectInfo(
            name="test-project",
            path="/test/path",
            project_id="proj-123",
            has_git=True,
            has_aios=False
        )
        handler = CommandHandler(project_info=project_info)

        result = handler.execute("/project --clear")

        assert "cleared" in result.lower()
        assert handler._project_info is None

    def test_project_clear_short(self):
        """Test that /project -c clears context."""
        project_info = ProjectInfo(
            name="test-project",
            path="/test/path",
            project_id="proj-123",
            has_git=True,
            has_aios=False
        )
        handler = CommandHandler(project_info=project_info)

        result = handler.execute("/project -c")

        assert "cleared" in result.lower()

    def test_project_detect(self):
        """Test that /project --detect triggers detection."""
        handler = CommandHandler()

        result = handler.execute("/project --detect")

        # Should either detect a project or say no project detected
        assert "project" in result.lower()

    def test_project_detect_short(self):
        """Test that /project -d triggers detection."""
        handler = CommandHandler()

        result = handler.execute("/project -d")

        assert "project" in result.lower()

    def test_project_set_explicit(self):
        """Test that /project <name> sets project."""
        handler = CommandHandler()

        result = handler.execute("/project my-new-project")

        assert "set to" in result.lower()
        assert "my-new-project" in result

    def test_project_no_context(self):
        """Test /project when no project context is set."""
        config = CLIConfig(auto_detect_project=False)
        handler = CommandHandler(config=config)
        handler._auto_detect_project = False

        result = handler.execute("/project")

        # Should indicate no project is set
        assert "No project" in result or "not set" in result.lower()

    def test_project_alias_proj(self):
        """Test that /proj alias works for project."""
        handler = CommandHandler()

        result = handler.execute("/proj")

        assert isinstance(result, str)

    def test_project_alias_p(self):
        """Test that /p alias works for project."""
        handler = CommandHandler()

        result = handler.execute("/p")

        assert isinstance(result, str)


# --- Status Command Tests ---


class TestCmdStatus:
    """Tests for /status command."""

    def test_status_returns_string(self):
        """Test that /status returns a string."""
        handler = CommandHandler()

        result = handler.execute("/status")

        assert isinstance(result, str)

    def test_status_shows_cli_status(self):
        """Test that /status shows CLI Status header."""
        handler = CommandHandler()

        result = handler.execute("/status")

        assert "CLI Status" in result

    def test_status_shows_project_section(self):
        """Test that /status shows Project section."""
        handler = CommandHandler()

        result = handler.execute("/status")

        assert "Project:" in result

    def test_status_shows_configuration(self):
        """Test that /status shows Configuration section."""
        handler = CommandHandler()

        result = handler.execute("/status")

        assert "Configuration:" in result

    def test_status_shows_backend(self):
        """Test that /status shows Backend section."""
        handler = CommandHandler()

        result = handler.execute("/status")

        assert "Backend:" in result

    def test_status_shows_commands(self):
        """Test that /status shows Commands section."""
        handler = CommandHandler()

        result = handler.execute("/status")

        assert "Commands:" in result
        assert "Registered:" in result

    def test_status_verbose(self):
        """Test that /status --verbose shows more detail."""
        handler = CommandHandler()

        result = handler.execute("/status --verbose")

        # Verbose should show backend URL and port
        assert "Backend URL:" in result or "backend_url" in result.lower()

    def test_status_verbose_short(self):
        """Test that /status -v shows more detail."""
        handler = CommandHandler()

        result = handler.execute("/status -v")

        assert isinstance(result, str)

    def test_status_alias_stat(self):
        """Test that /stat alias works for status."""
        handler = CommandHandler()

        result = handler.execute("/stat")

        assert "CLI Status" in result


# --- Recent Command Tests ---


class TestCmdRecent:
    """Tests for /recent command."""

    def test_recent_returns_string(self):
        """Test that /recent returns a string."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/recent")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_recent_with_limit(self):
        """Test that /recent --limit N works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/recent --limit 5")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_recent_with_limit_short(self):
        """Test that /recent -l N works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/recent -l 5")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_recent_with_verbose(self):
        """Test that /recent --verbose works."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/recent --verbose")

        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_recent_alias_r(self):
        """Test that /r alias works for recent."""
        handler = CommandHandler()
        handler.query_engine.connect()

        result = handler.execute("/r")

        assert isinstance(result, str)

        handler.query_engine.disconnect()


# --- Integration Tests ---


class TestCommandsIntegration:
    """Integration tests for commands module."""

    def test_all_commands_executable(self):
        """Test that all registered commands are executable."""
        handler = CommandHandler()
        handler.query_engine.connect()

        for cmd_name, cmd_info in COMMANDS.items():
            if cmd_name == cmd_info.name:  # Only test main names
                result = handler.execute(f"/{cmd_name}")
                assert isinstance(result, str), f"/{cmd_name} didn't return string"

        handler.query_engine.disconnect()

    def test_commands_with_project_context(self):
        """Test commands with project context."""
        project_info = ProjectInfo(
            name="test-project",
            path="/test/path",
            project_id="proj-123",
            has_git=True,
            has_aios=False
        )
        handler = CommandHandler(project_info=project_info)
        handler.query_engine.connect()

        # Test various commands work with project context
        assert isinstance(handler.execute("/status"), str)
        assert isinstance(handler.execute("/project"), str)
        assert isinstance(handler.execute("/tasks"), str)

        handler.query_engine.disconnect()

    def test_help_command_matches_registered(self):
        """Test that help output matches registered commands."""
        handler = CommandHandler()

        help_output = handler.execute("/help")

        # All main command names should appear in help
        for cmd_name, cmd_info in COMMANDS.items():
            if cmd_name == cmd_info.name:  # Only main names
                assert f"/{cmd_name}" in help_output, f"/{cmd_name} not in help"

    def test_command_error_handling(self):
        """Test that commands handle errors gracefully."""
        handler = CommandHandler()

        # Unknown commands should return error string, not raise
        result = handler.execute("/nonexistent")
        assert isinstance(result, str)
        assert "Unknown" in result or "Error" in result

    def test_search_with_node_data(self):
        """Test search command with actual node data."""
        handler = CommandHandler()
        handler.query_engine.connect()

        # Add searchable nodes
        nodes = [
            Node(type="task", content="Implement authentication", embedding=[0.9, 0.5, 0.0, 0.0, 0.0]),
            Node(type="decision", content="Use JWT tokens", embedding=[0.85, 0.55, 0.0, 0.0, 0.0]),
            Node(type="task", content="Write tests", embedding=[0.0, 0.0, 0.9, 0.5, 0.0]),
        ]

        for node in nodes:
            handler.query_engine._client.add_node(node)

        # Search should find relevant results
        result = handler.execute("/search authentication")
        assert isinstance(result, str)

        handler.query_engine.disconnect()

    def test_json_output_format(self):
        """Test commands with JSON output format."""
        config = CLIConfig(output_format="json")
        handler = CommandHandler(config=config)
        handler.query_engine.connect()

        result = handler.execute("/tasks")

        # Should be valid JSON (or "no tasks" message)
        if "No tasks" not in result:
            try:
                json.loads(result)
            except json.JSONDecodeError:
                pytest.fail("Tasks output was not valid JSON")

        handler.query_engine.disconnect()

    def test_table_output_format(self):
        """Test commands with table output format."""
        config = CLIConfig(output_format="table")
        handler = CommandHandler(config=config)
        handler.query_engine.connect()

        result = handler.execute("/tasks")

        # Should contain table structure or "no tasks" message
        assert isinstance(result, str)

        handler.query_engine.disconnect()
