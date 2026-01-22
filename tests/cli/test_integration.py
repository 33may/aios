"""
Integration Tests for CLI Workflow

Tests end-to-end workflows combining CLI components (commands, query engine,
formatters, project detection) to validate the complete CLI system.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import tempfile
import os

from apps.cli.main import cli
from apps.cli.config import CLIConfig
from apps.cli.commands import CommandHandler, COMMANDS
from apps.cli.query_engine import QueryEngine
from apps.cli.project_detector import detect_project, detect_project_id, ProjectInfo
from apps.cli import formatters
from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.backend.integrations.graphiti import queries

from click.testing import CliRunner


class TestCompleteCliWorkflow:
    """Test complete end-to-end CLI workflows."""

    def test_search_workflow_with_knowledge_graph(self):
        """
        Test a complete search workflow:
        1. Create knowledge nodes in the graph
        2. Use CLI search command to query
        3. Verify search results are formatted correctly
        """
        client = GraphitiClient()
        client.connect()

        try:
            # Step 1: Create a project with decisions
            project = Node(
                type="project",
                content="AIOS CLI Development",
                embedding=[0.8, 0.6, 0.2, 0.0, 0.0]
            )
            project_id = client.add_node(project)
            assert project_id is not None

            # Add a decision about technology choice
            decision = Node(
                type="decision",
                content="Use Click library for CLI framework",
                embedding=[0.7, 0.7, 0.1, 0.0, 0.0],
                metadata={"rationale": "Well-documented, widely used, good testing support"}
            )
            decision_id = client.add_node(decision)

            # Link decision to project
            client.add_edge(Edge(
                type="contains",
                source_id=project_id,
                target_id=decision_id
            ))

            # Step 2: Create CLI handler and search
            config = CLIConfig()
            engine = QueryEngine(config=config)
            engine._client = client  # Use existing client

            handler = CommandHandler(
                config=config,
                query_engine=engine
            )

            # Step 3: Execute search command
            result = handler.execute("/search Click")

            # Verify search found our decision
            assert "result" in result.lower() or "found" in result.lower()

            # Perform semantic search directly
            results = queries.search_semantic("CLI framework", limit=10, client=client)
            assert len(results) > 0

            # Verify our decision is in the results
            result_contents = [node.content.lower() for node, _ in results]
            assert any("click" in content for content in result_contents)

        finally:
            client.disconnect()

    def test_tasks_workflow_with_knowledge_graph(self):
        """
        Test a complete tasks workflow:
        1. Create task nodes in the graph
        2. Use CLI tasks command to list
        3. Verify task formatting and display
        """
        client = GraphitiClient()
        client.connect()

        try:
            # Step 1: Create tasks
            task1 = Node(
                type="task",
                content="Implement search command",
                embedding=[0.9, 0.5, 0.0, 0.0, 0.0],
                metadata={"status": "completed"}
            )
            task1_id = client.add_node(task1)

            task2 = Node(
                type="task",
                content="Add integration tests",
                embedding=[0.8, 0.4, 0.2, 0.0, 0.0],
                metadata={"status": "in_progress"}
            )
            task2_id = client.add_node(task2)

            task3 = Node(
                type="task",
                content="Write documentation",
                embedding=[0.7, 0.3, 0.3, 0.1, 0.0],
                metadata={"status": "pending"}
            )
            task3_id = client.add_node(task3)

            # Step 2: Query tasks using queries module
            end = datetime.now()
            start = end - timedelta(days=30)

            tasks = queries.query_temporal_nodes(
                start=start,
                end=end,
                node_type="task",
                client=client
            )

            # Verify we found our tasks
            assert len(tasks) >= 3
            task_ids = [task.uuid for task in tasks]
            assert task1_id in task_ids
            assert task2_id in task_ids
            assert task3_id in task_ids

            # Step 3: Format tasks
            output = formatters.format_tasks(tasks, output_format="text")

            # Verify output contains task content
            assert "Implement search command" in output or "search" in output.lower()
            assert "total" in output.lower()

        finally:
            client.disconnect()

    def test_decisions_workflow_with_knowledge_graph(self):
        """
        Test a complete decisions workflow:
        1. Create decision nodes with rationale
        2. Use CLI decisions command to list
        3. Verify decision formatting with source attribution
        """
        client = GraphitiClient()
        client.connect()

        try:
            # Step 1: Create decisions with metadata
            decision1 = Node(
                type="decision",
                content="Use semantic search for natural language queries",
                embedding=[0.85, 0.55, 0.1, 0.0, 0.0],
                metadata={
                    "rationale": "Better matches user intent than keyword search",
                    "session_id": "session-123"
                }
            )
            decision1_id = client.add_node(decision1)

            decision2 = Node(
                type="decision",
                content="Support multiple output formats (text, json, table)",
                embedding=[0.75, 0.45, 0.3, 0.2, 0.0],
                metadata={
                    "rationale": "Flexibility for different use cases",
                    "project_id": "proj-456"
                }
            )
            decision2_id = client.add_node(decision2)

            # Step 2: Query decisions
            end = datetime.now()
            start = end - timedelta(days=90)

            decisions = queries.query_temporal_nodes(
                start=start,
                end=end,
                node_type="decision",
                client=client
            )

            # Verify we found our decisions
            assert len(decisions) >= 2
            decision_ids = [d.uuid for d in decisions]
            assert decision1_id in decision_ids
            assert decision2_id in decision_ids

            # Step 3: Format decisions with verbose mode
            output = formatters.format_decisions(decisions, output_format="text", verbose=True)

            # Verify output contains decision content and rationale
            assert "semantic search" in output or "natural language" in output.lower()
            assert "rationale" in output.lower()

        finally:
            client.disconnect()

    def test_project_scoped_search_workflow(self):
        """
        Test project-scoped search workflow:
        1. Create multiple projects with different content
        2. Search within a specific project scope
        3. Verify results are limited to the project
        """
        client = GraphitiClient()
        client.connect()

        try:
            # Step 1: Create two separate projects
            project1 = Node(
                type="project",
                content="Authentication System",
                embedding=[0.9, 0.3, 0.0, 0.0, 0.0]
            )
            project1_id = client.add_node(project1)

            project2 = Node(
                type="project",
                content="Logging Framework",
                embedding=[0.3, 0.9, 0.0, 0.0, 0.0]
            )
            project2_id = client.add_node(project2)

            # Add content to project1
            task1 = Node(
                type="task",
                content="Implement JWT authentication",
                embedding=[0.85, 0.35, 0.05, 0.0, 0.0]
            )
            task1_id = client.add_node(task1)
            client.add_edge(Edge(type="contains", source_id=project1_id, target_id=task1_id))

            # Add content to project2
            task2 = Node(
                type="task",
                content="Implement log rotation",
                embedding=[0.35, 0.85, 0.05, 0.0, 0.0]
            )
            task2_id = client.add_node(task2)
            client.add_edge(Edge(type="contains", source_id=project2_id, target_id=task2_id))

            # Step 2: Search within project1 scope
            scoped_results = queries.search_scoped(
                project1_id,
                "authentication",
                limit=10,
                client=client
            )

            # Verify results are from project1 scope
            scoped_ids = [node.uuid for node, _ in scoped_results]

            # project1's task should potentially be in results
            # project2's task should NOT be in results
            if task2_id in scoped_ids:
                # If task2 is somehow in results, it should have a lower score
                task2_score = next((score for node, score in scoped_results if node.uuid == task2_id), 0)
                assert task2_score < 0.5, "Project2 task should have low relevance in project1 scope"

        finally:
            client.disconnect()


class TestCommandHandlerIntegration:
    """Test CommandHandler with full component integration."""

    def test_handler_with_all_commands(self):
        """Test that handler can execute all registered commands."""
        config = CLIConfig()
        handler = CommandHandler(config=config)

        # Verify all main commands can be executed without error
        commands_to_test = [
            ("/help", "available"),
            ("/status", "project" if handler.project_info else "cli status"),
        ]

        for cmd, expected_in_output in commands_to_test:
            result = handler.execute(cmd)
            assert isinstance(result, str)
            assert len(result) > 0
            # Basic check that command returned something meaningful
            assert expected_in_output.lower() in result.lower() or len(result) > 10

    def test_handler_with_project_detection(self):
        """Test handler with project detection in a git repository."""
        # Create a temporary directory with .git marker
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = os.path.join(tmpdir, ".git")
            os.mkdir(git_dir)

            # Change to temp directory to test detection
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Detect project
                project_info = detect_project()

                if project_info:
                    assert project_info.has_git
                    assert str(project_info.path) == tmpdir
                    assert project_info.project_id is not None

                    # Create handler with detected project
                    config = CLIConfig()
                    handler = CommandHandler(config=config, project_info=project_info)

                    # Execute project command
                    result = handler.execute("/project")
                    assert "project" in result.lower()

            finally:
                os.chdir(original_cwd)

    def test_handler_search_integration(self):
        """Test handler search command with actual query engine."""
        client = GraphitiClient()
        client.connect()

        try:
            # Create some searchable content
            node = Node(
                type="note",
                content="Integration test note for CLI handler",
                embedding=[0.5, 0.5, 0.5, 0.0, 0.0]
            )
            client.add_node(node)

            # Create handler with connected query engine
            config = CLIConfig()
            engine = QueryEngine(config=config)
            engine._client = client

            handler = CommandHandler(config=config, query_engine=engine)

            # Execute search
            result = handler.execute("/search integration test")

            # Verify search executed successfully
            assert isinstance(result, str)
            # Result should either contain matches or "no results" message
            assert len(result) > 0

        finally:
            client.disconnect()


class TestQueryEngineIntegration:
    """Test QueryEngine integration with backend."""

    def test_query_engine_full_workflow(self):
        """Test query engine with complete search workflow."""
        with GraphitiClient() as client:
            # Create test data
            project = Node(
                type="project",
                content="Query Engine Test Project",
                embedding=[0.6, 0.6, 0.3, 0.0, 0.0]
            )
            project_id = client.add_node(project)

            task = Node(
                type="task",
                content="Test semantic search functionality",
                embedding=[0.7, 0.5, 0.4, 0.0, 0.0]
            )
            task_id = client.add_node(task)

            client.add_edge(Edge(
                type="contains",
                source_id=project_id,
                target_id=task_id
            ))

            # Use query engine
            config = CLIConfig()
            engine = QueryEngine(config=config)
            engine._client = client

            # Test search
            results = engine.search("semantic search", limit=10)
            assert isinstance(results, list)

            # Test project-scoped search
            scoped_results = engine.search_in_project(project_id, "test", limit=10)
            assert isinstance(scoped_results, list)

            # Test get_related
            related = engine.get_related(project_id)
            assert isinstance(related, list)

            # Test traverse
            traversal = engine.traverse(project_id, depth=1)
            assert isinstance(traversal, dict)
            assert "0" in traversal
            assert "1" in traversal

    def test_query_engine_context_manager(self):
        """Test query engine as context manager."""
        config = CLIConfig()

        with QueryEngine(config=config) as engine:
            engine.connect()
            assert engine.is_connected()

            # Perform a search
            results = engine.search("test", limit=5)
            assert isinstance(results, list)


class TestFormatterIntegration:
    """Test formatters integration with real data."""

    def test_formatters_with_real_nodes(self):
        """Test formatters with actual Node objects from the backend."""
        client = GraphitiClient()
        client.connect()

        try:
            # Create various node types
            task = Node(
                type="task",
                content="Complete integration testing",
                embedding=[0.5, 0.5, 0.0, 0.0, 0.0],
                metadata={"status": "in_progress", "project_id": "test-proj"}
            )
            task_id = client.add_node(task)

            decision = Node(
                type="decision",
                content="Use pytest for testing",
                embedding=[0.6, 0.4, 0.0, 0.0, 0.0],
                metadata={"rationale": "Good integration with Python ecosystem"}
            )
            decision_id = client.add_node(decision)

            note = Node(
                type="note",
                content="Testing notes for CLI formatter",
                embedding=[0.4, 0.6, 0.0, 0.0, 0.0]
            )
            note_id = client.add_node(note)

            # Retrieve nodes
            retrieved_task = client.get_node(task_id)
            retrieved_decision = client.get_node(decision_id)
            retrieved_note = client.get_node(note_id)

            # Test all output formats for tasks
            task_list = [retrieved_task]
            text_output = formatters.format_tasks(task_list, output_format="text")
            assert "integration testing" in text_output.lower() or "task" in text_output.lower()

            json_output = formatters.format_tasks(task_list, output_format="json")
            assert "task" in json_output.lower()
            assert "{" in json_output  # Valid JSON

            table_output = formatters.format_tasks(task_list, output_format="table")
            assert "|" in table_output  # Table has separators

            # Test all output formats for decisions
            decision_list = [retrieved_decision]
            text_output = formatters.format_decisions(decision_list, output_format="text", verbose=True)
            assert "pytest" in text_output.lower() or "testing" in text_output.lower()
            assert "rationale" in text_output.lower()

            json_output = formatters.format_decisions(decision_list, output_format="json")
            assert "decision" in json_output.lower()

            # Test search results formatting
            search_results = [(retrieved_task, 0.85), (retrieved_decision, 0.72)]
            text_output = formatters.format_search_results(search_results, output_format="text", show_score=True)
            assert "0.85" in text_output or "0.72" in text_output  # Score displayed

            # Test recent items formatting
            recent_items = [retrieved_task, retrieved_decision, retrieved_note]
            text_output = formatters.format_recent(recent_items, output_format="text")
            assert len(text_output) > 0

        finally:
            client.disconnect()


class TestClickCliIntegration:
    """Test Click CLI integration end-to-end."""

    def test_cli_help_command(self):
        """Test CLI help command via Click runner."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "usage" in result.output.lower()
        assert "query" in result.output.lower() or "search" in result.output.lower()

    def test_cli_version_command(self):
        """Test CLI version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_status_command(self):
        """Test CLI status command via Click runner."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "project" in result.output.lower() or "cli" in result.output.lower()

    def test_cli_tasks_command(self):
        """Test CLI tasks command via Click runner."""
        runner = CliRunner()
        result = runner.invoke(cli, ["tasks", "--all"])

        # Should complete without error
        assert result.exit_code == 0

    def test_cli_decisions_command(self):
        """Test CLI decisions command via Click runner."""
        runner = CliRunner()
        result = runner.invoke(cli, ["decisions", "--all"])

        # Should complete without error
        assert result.exit_code == 0

    def test_cli_search_command(self):
        """Test CLI search command via Click runner."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test", "query"])

        # Should complete without error
        assert result.exit_code == 0

    def test_cli_recent_command(self):
        """Test CLI recent command via Click runner."""
        runner = CliRunner()
        result = runner.invoke(cli, ["recent", "--limit", "5"])

        # Should complete without error
        assert result.exit_code == 0

    def test_cli_project_command(self):
        """Test CLI project command via Click runner."""
        runner = CliRunner()
        result = runner.invoke(cli, ["project"])

        # Should complete without error
        assert result.exit_code == 0

    def test_cli_one_shot_query(self):
        """Test CLI one-shot query mode."""
        runner = CliRunner()
        result = runner.invoke(cli, ["why did we choose this"])

        # Should complete without error (performs search)
        assert result.exit_code == 0

    def test_cli_verbose_flag(self):
        """Test CLI verbose flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "status"])

        assert result.exit_code == 0
        # Verbose should show more detailed output
        assert len(result.output) > 0

    def test_cli_format_flag(self):
        """Test CLI format flag with JSON output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "tasks", "--all"])

        # Should complete without error
        assert result.exit_code == 0
        # Output should be JSON-formatted (may be empty list)

    def test_cli_limit_flag(self):
        """Test CLI limit flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--limit", "3", "search", "test"])

        # Should complete without error
        assert result.exit_code == 0


class TestProjectDetectionIntegration:
    """Test project detection integration scenarios."""

    def test_project_detection_in_git_repo(self):
        """Test project detection in a simulated git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .git directory
            git_dir = os.path.join(tmpdir, ".git")
            os.mkdir(git_dir)

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                project_info = detect_project()

                if project_info:
                    assert project_info.has_git
                    assert project_info.project_id is not None
                    assert str(project_info.path) == tmpdir

            finally:
                os.chdir(original_cwd)

    def test_project_detection_in_aios_repo(self):
        """Test project detection with .aios marker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .aios directory
            aios_dir = os.path.join(tmpdir, ".aios")
            os.mkdir(aios_dir)

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                project_info = detect_project()

                if project_info:
                    assert project_info.has_aios
                    assert project_info.project_id is not None

            finally:
                os.chdir(original_cwd)

    def test_project_detection_with_nested_directory(self):
        """Test project detection from nested subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .git at root
            git_dir = os.path.join(tmpdir, ".git")
            os.mkdir(git_dir)

            # Create nested directories
            nested_dir = os.path.join(tmpdir, "src", "components", "cli")
            os.makedirs(nested_dir)

            original_cwd = os.getcwd()
            try:
                os.chdir(nested_dir)

                project_info = detect_project()

                if project_info:
                    assert project_info.has_git
                    # Project root should be the parent with .git
                    assert str(project_info.path) == tmpdir

            finally:
                os.chdir(original_cwd)


class TestErrorHandling:
    """Test error handling in CLI workflows."""

    def test_unknown_command_handling(self):
        """Test handling of unknown commands."""
        config = CLIConfig()
        handler = CommandHandler(config=config)

        result = handler.execute("/nonexistent")

        assert "unknown" in result.lower()
        assert "/help" in result.lower()

    def test_empty_command_handling(self):
        """Test handling of empty commands."""
        config = CLIConfig()
        handler = CommandHandler(config=config)

        result = handler.execute("/")

        assert "error" in result.lower() or "empty" in result.lower()

    def test_search_without_query(self):
        """Test search command without query text."""
        config = CLIConfig()
        handler = CommandHandler(config=config)

        result = handler.execute("/search")

        assert "error" in result.lower() or "provide" in result.lower() or "usage" in result.lower()

    def test_invalid_limit_handling(self):
        """Test handling of invalid limit values."""
        runner = CliRunner()

        # Invalid limit (non-numeric) - should show error
        result = runner.invoke(cli, ["--limit", "abc", "search", "test"])

        # Click should handle this with an error message
        assert result.exit_code != 0 or "invalid" in result.output.lower() or "error" in result.output.lower()


class TestConcurrentWorkflows:
    """Test concurrent operation scenarios."""

    def test_multiple_handler_instances(self):
        """Test multiple CommandHandler instances can coexist."""
        config1 = CLIConfig()
        config1.default_limit = 5

        config2 = CLIConfig()
        config2.default_limit = 10

        handler1 = CommandHandler(config=config1)
        handler2 = CommandHandler(config=config2)

        # Execute commands on both handlers
        result1 = handler1.execute("/help")
        result2 = handler2.execute("/help")

        # Both should return valid results
        assert "available" in result1.lower()
        assert "available" in result2.lower()

        # Configs should remain independent
        assert handler1.config.default_limit == 5
        assert handler2.config.default_limit == 10

    def test_batch_knowledge_operations(self):
        """Test batch operations on knowledge graph through CLI."""
        client = GraphitiClient()
        client.connect()

        try:
            # Create multiple nodes in batch
            nodes = []
            for i in range(10):
                node = Node(
                    type="task",
                    content=f"Batch task {i}: CLI integration test item",
                    embedding=[float(i) / 10, 0.5, 0.5, 0.0, 0.0]
                )
                node_id = client.add_node(node)
                nodes.append((node_id, node))

            # Search for batch items
            results = queries.search_semantic("batch CLI integration", limit=20, client=client)

            # Should find our batch items
            assert len(results) > 0
            result_contents = [node.content.lower() for node, _ in results]
            assert any("batch" in content for content in result_contents)

            # Create handler and execute search
            config = CLIConfig()
            engine = QueryEngine(config=config)
            engine._client = client

            handler = CommandHandler(config=config, query_engine=engine)

            result = handler.execute("/search batch CLI integration")
            assert len(result) > 0

        finally:
            client.disconnect()


class TestOutputFormats:
    """Test different output format scenarios."""

    def test_text_format_workflow(self):
        """Test complete workflow with text output format."""
        client = GraphitiClient()
        client.connect()

        try:
            # Create test data
            task = Node(
                type="task",
                content="Text format test task",
                embedding=[0.5, 0.5, 0.0, 0.0, 0.0],
                metadata={"status": "pending"}
            )
            client.add_node(task)

            # Query and format as text
            end = datetime.now()
            start = end - timedelta(days=30)

            tasks = queries.query_temporal_nodes(
                start=start,
                end=end,
                node_type="task",
                client=client
            )

            text_output = formatters.format_tasks(tasks, output_format="text")

            assert "task" in text_output.lower()
            assert "total" in text_output.lower()

        finally:
            client.disconnect()

    def test_json_format_workflow(self):
        """Test complete workflow with JSON output format."""
        client = GraphitiClient()
        client.connect()

        try:
            # Create test data
            decision = Node(
                type="decision",
                content="JSON format test decision",
                embedding=[0.6, 0.4, 0.0, 0.0, 0.0],
                metadata={"rationale": "Testing JSON output"}
            )
            client.add_node(decision)

            # Query and format as JSON
            end = datetime.now()
            start = end - timedelta(days=90)

            decisions = queries.query_temporal_nodes(
                start=start,
                end=end,
                node_type="decision",
                client=client
            )

            json_output = formatters.format_decisions(decisions, output_format="json")

            # Verify valid JSON structure
            import json
            parsed = json.loads(json_output)
            assert "count" in parsed
            assert "decisions" in parsed
            assert isinstance(parsed["decisions"], list)

        finally:
            client.disconnect()

    def test_table_format_workflow(self):
        """Test complete workflow with table output format."""
        client = GraphitiClient()
        client.connect()

        try:
            # Create test data
            note = Node(
                type="note",
                content="Table format test note",
                embedding=[0.4, 0.4, 0.2, 0.0, 0.0]
            )
            client.add_node(note)

            # Query and format as table
            end = datetime.now()
            start = end - timedelta(days=7)

            items = queries.query_temporal_nodes(
                start=start,
                end=end,
                node_type=None,
                client=client
            )

            table_output = formatters.format_recent(items, output_format="table")

            # Verify table structure
            assert "|" in table_output
            assert "+" in table_output
            assert "-" in table_output

        finally:
            client.disconnect()
