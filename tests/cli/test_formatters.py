"""
Tests for CLI Output Formatters

Tests formatting functions for displaying query results from the knowledge graph.
Covers all output formats (text, json, table) and specialized formatters
for different node types (tasks, decisions, sessions, recent items).
"""

import pytest
import json
from datetime import datetime, timedelta

from apps.cli.formatters import (
    format_search_results,
    format_node,
    format_tasks,
    format_decisions,
    format_recent,
    _format_empty_results,
    _format_timestamp,
    _truncate_content,
    _get_task_status,
    _get_task_checkbox,
    _get_decision_rationale,
    _get_source_attribution,
    _format_source_line,
    _node_to_dict,
    _build_ascii_table,
)
from apps.backend.integrations.graphiti.models import Node


# --- Helper Function Tests ---


class TestFormatTimestamp:
    """Tests for timestamp formatting."""

    def test_format_timestamp_basic(self):
        """Test basic timestamp formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = _format_timestamp(dt)

        assert result == "2024-01-15 10:30:45"

    def test_format_timestamp_midnight(self):
        """Test formatting midnight timestamp."""
        dt = datetime(2024, 1, 1, 0, 0, 0)
        result = _format_timestamp(dt)

        assert result == "2024-01-01 00:00:00"

    def test_format_timestamp_end_of_day(self):
        """Test formatting end of day timestamp."""
        dt = datetime(2024, 12, 31, 23, 59, 59)
        result = _format_timestamp(dt)

        assert result == "2024-12-31 23:59:59"


class TestTruncateContent:
    """Tests for content truncation."""

    def test_truncate_content_short_string(self):
        """Test that short strings are not truncated."""
        content = "Short content"
        result = _truncate_content(content, max_length=80)

        assert result == content

    def test_truncate_content_exact_length(self):
        """Test content at exact max length."""
        content = "A" * 80
        result = _truncate_content(content, max_length=80)

        assert result == content
        assert len(result) == 80

    def test_truncate_content_too_long(self):
        """Test that long strings are truncated with ellipsis."""
        content = "A" * 100
        result = _truncate_content(content, max_length=80)

        assert len(result) == 80
        assert result.endswith("...")

    def test_truncate_content_custom_length(self):
        """Test truncation with custom max length."""
        content = "A" * 50
        result = _truncate_content(content, max_length=30)

        assert len(result) == 30
        assert result.endswith("...")

    def test_truncate_content_default_length(self):
        """Test default max length of 80."""
        content = "A" * 100
        result = _truncate_content(content)

        assert len(result) == 80


class TestGetTaskStatus:
    """Tests for task status extraction."""

    def test_get_task_status_from_metadata(self):
        """Test extracting status from node metadata."""
        node = Node(type="task", content="Test", metadata={"status": "in_progress"})
        result = _get_task_status(node)

        assert result == "in_progress"

    def test_get_task_status_default(self):
        """Test default status when not in metadata."""
        node = Node(type="task", content="Test", metadata={})
        result = _get_task_status(node)

        assert result == "pending"

    def test_get_task_status_no_metadata(self):
        """Test default status when metadata is None."""
        node = Node(type="task", content="Test", metadata=None)
        result = _get_task_status(node)

        assert result == "pending"

    def test_get_task_status_completed(self):
        """Test extracting completed status."""
        node = Node(type="task", content="Test", metadata={"status": "completed"})
        result = _get_task_status(node)

        assert result == "completed"


class TestGetTaskCheckbox:
    """Tests for task checkbox representation."""

    def test_get_task_checkbox_pending(self):
        """Test checkbox for pending task."""
        node = Node(type="task", content="Test", metadata={"status": "pending"})
        result = _get_task_checkbox(node)

        assert result == "[ ]"

    def test_get_task_checkbox_completed(self):
        """Test checkbox for completed task."""
        node = Node(type="task", content="Test", metadata={"status": "completed"})
        result = _get_task_checkbox(node)

        assert result == "[x]"

    def test_get_task_checkbox_done(self):
        """Test checkbox for done status."""
        node = Node(type="task", content="Test", metadata={"status": "done"})
        result = _get_task_checkbox(node)

        assert result == "[x]"

    def test_get_task_checkbox_finished(self):
        """Test checkbox for finished status."""
        node = Node(type="task", content="Test", metadata={"status": "finished"})
        result = _get_task_checkbox(node)

        assert result == "[x]"

    def test_get_task_checkbox_in_progress(self):
        """Test checkbox for in_progress task."""
        node = Node(type="task", content="Test", metadata={"status": "in_progress"})
        result = _get_task_checkbox(node)

        assert result == "[-]"

    def test_get_task_checkbox_active(self):
        """Test checkbox for active status."""
        node = Node(type="task", content="Test", metadata={"status": "active"})
        result = _get_task_checkbox(node)

        assert result == "[-]"

    def test_get_task_checkbox_working(self):
        """Test checkbox for working status."""
        node = Node(type="task", content="Test", metadata={"status": "working"})
        result = _get_task_checkbox(node)

        assert result == "[-]"

    def test_get_task_checkbox_no_metadata(self):
        """Test default checkbox when no metadata."""
        node = Node(type="task", content="Test", metadata=None)
        result = _get_task_checkbox(node)

        assert result == "[ ]"


class TestGetDecisionRationale:
    """Tests for decision rationale extraction."""

    def test_get_decision_rationale_from_rationale_field(self):
        """Test extracting rationale from 'rationale' field."""
        node = Node(type="decision", content="Use JWT", metadata={"rationale": "Stateless auth"})
        result = _get_decision_rationale(node)

        assert result == "Stateless auth"

    def test_get_decision_rationale_from_reason_field(self):
        """Test extracting rationale from 'reason' field."""
        node = Node(type="decision", content="Use JWT", metadata={"reason": "Better security"})
        result = _get_decision_rationale(node)

        assert result == "Better security"

    def test_get_decision_rationale_from_why_field(self):
        """Test extracting rationale from 'why' field."""
        node = Node(type="decision", content="Use JWT", metadata={"why": "Performance"})
        result = _get_decision_rationale(node)

        assert result == "Performance"

    def test_get_decision_rationale_from_justification_field(self):
        """Test extracting rationale from 'justification' field."""
        node = Node(type="decision", content="Use JWT", metadata={"justification": "Industry standard"})
        result = _get_decision_rationale(node)

        assert result == "Industry standard"

    def test_get_decision_rationale_from_explanation_field(self):
        """Test extracting rationale from 'explanation' field."""
        node = Node(type="decision", content="Use JWT", metadata={"explanation": "Scalable"})
        result = _get_decision_rationale(node)

        assert result == "Scalable"

    def test_get_decision_rationale_no_metadata(self):
        """Test None when no metadata."""
        node = Node(type="decision", content="Use JWT", metadata=None)
        result = _get_decision_rationale(node)

        assert result is None

    def test_get_decision_rationale_empty_metadata(self):
        """Test None when metadata has no rationale fields."""
        node = Node(type="decision", content="Use JWT", metadata={"other": "value"})
        result = _get_decision_rationale(node)

        assert result is None

    def test_get_decision_rationale_empty_value(self):
        """Test None when rationale field is empty."""
        node = Node(type="decision", content="Use JWT", metadata={"rationale": ""})
        result = _get_decision_rationale(node)

        assert result is None

    def test_get_decision_rationale_priority_order(self):
        """Test that 'rationale' field has priority."""
        node = Node(
            type="decision",
            content="Use JWT",
            metadata={"rationale": "First", "reason": "Second", "why": "Third"}
        )
        result = _get_decision_rationale(node)

        assert result == "First"


class TestGetSourceAttribution:
    """Tests for source attribution extraction."""

    def test_get_source_attribution_session_id(self):
        """Test source from session_id field."""
        node = Node(type="task", content="Test", metadata={"session_id": "sess-123"})
        result = _get_source_attribution(node)

        assert result == "session:sess-123"

    def test_get_source_attribution_session(self):
        """Test source from session field."""
        node = Node(type="task", content="Test", metadata={"session": "work-session"})
        result = _get_source_attribution(node)

        assert result == "session:work-session"

    def test_get_source_attribution_project_id(self):
        """Test source from project_id field."""
        node = Node(type="task", content="Test", metadata={"project_id": "proj-456"})
        result = _get_source_attribution(node)

        assert result == "project:proj-456"

    def test_get_source_attribution_project(self):
        """Test source from project field."""
        node = Node(type="task", content="Test", metadata={"project": "my-project"})
        result = _get_source_attribution(node)

        assert result == "project:my-project"

    def test_get_source_attribution_source_file(self):
        """Test source from source_file field."""
        node = Node(type="task", content="Test", metadata={"source_file": "main.py"})
        result = _get_source_attribution(node)

        assert result == "file:main.py"

    def test_get_source_attribution_source(self):
        """Test source from source field (no prefix)."""
        node = Node(type="task", content="Test", metadata={"source": "manual input"})
        result = _get_source_attribution(node)

        assert result == "manual input"

    def test_get_source_attribution_file(self):
        """Test source from file field."""
        node = Node(type="task", content="Test", metadata={"file": "config.json"})
        result = _get_source_attribution(node)

        assert result == "file:config.json"

    def test_get_source_attribution_origin(self):
        """Test source from origin field (no prefix)."""
        node = Node(type="task", content="Test", metadata={"origin": "user input"})
        result = _get_source_attribution(node)

        assert result == "user input"

    def test_get_source_attribution_priority_order(self):
        """Test that session_id has highest priority."""
        node = Node(
            type="task",
            content="Test",
            metadata={
                "session_id": "sess-123",
                "project_id": "proj-456",
                "source_file": "test.py"
            }
        )
        result = _get_source_attribution(node)

        assert result == "session:sess-123"

    def test_get_source_attribution_no_metadata(self):
        """Test None when no metadata."""
        node = Node(type="task", content="Test", metadata=None)
        result = _get_source_attribution(node)

        assert result is None

    def test_get_source_attribution_empty_metadata(self):
        """Test None when metadata has no source fields."""
        node = Node(type="task", content="Test", metadata={"other": "value"})
        result = _get_source_attribution(node)

        assert result is None

    def test_get_source_attribution_empty_value(self):
        """Test None when source field is empty."""
        node = Node(type="task", content="Test", metadata={"session_id": ""})
        result = _get_source_attribution(node)

        assert result is None


class TestFormatSourceLine:
    """Tests for source line formatting."""

    def test_format_source_line_with_source(self):
        """Test formatting source line when source exists."""
        node = Node(type="task", content="Test", metadata={"session_id": "sess-123"})
        result = _format_source_line(node)

        assert result == "   Source: session:sess-123"

    def test_format_source_line_no_source(self):
        """Test empty string when no source."""
        node = Node(type="task", content="Test", metadata=None)
        result = _format_source_line(node)

        assert result == ""


class TestFormatEmptyResults:
    """Tests for empty results formatting."""

    def test_format_empty_results_text(self):
        """Test empty results in text format."""
        result = _format_empty_results("text", "search results")

        assert result == "No search results found."

    def test_format_empty_results_table(self):
        """Test empty results in table format."""
        result = _format_empty_results("table", "tasks")

        assert result == "No tasks found."

    def test_format_empty_results_json(self):
        """Test empty results in JSON format."""
        result = _format_empty_results("json", "decisions")

        data = json.loads(result)
        assert data["results"] == []
        assert data["count"] == 0


class TestNodeToDict:
    """Tests for node to dictionary conversion."""

    def test_node_to_dict_basic(self):
        """Test basic node conversion."""
        node = Node(type="task", content="Test task")
        result = _node_to_dict(node, verbose=False)

        assert result["type"] == "task"
        assert result["content"] == "Test task"
        assert "uuid" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_node_to_dict_with_source(self):
        """Test node conversion includes source attribution."""
        node = Node(type="task", content="Test", metadata={"session_id": "sess-123"})
        result = _node_to_dict(node, verbose=False)

        assert result["source"] == "session:sess-123"

    def test_node_to_dict_verbose(self):
        """Test verbose mode includes metadata."""
        node = Node(type="task", content="Test", metadata={"priority": "high", "status": "pending"})
        result = _node_to_dict(node, verbose=True)

        assert "metadata" in result
        assert result["metadata"]["priority"] == "high"

    def test_node_to_dict_non_verbose_excludes_metadata(self):
        """Test non-verbose mode excludes metadata."""
        node = Node(type="task", content="Test", metadata={"priority": "high"})
        result = _node_to_dict(node, verbose=False)

        assert "metadata" not in result


class TestBuildAsciiTable:
    """Tests for ASCII table building."""

    def test_build_ascii_table_basic(self):
        """Test basic table building."""
        headers = ["Name", "Value"]
        rows = [["foo", "bar"], ["baz", "qux"]]
        result = _build_ascii_table(headers, rows)

        assert "Name" in result
        assert "Value" in result
        assert "foo" in result
        assert "bar" in result
        assert "+" in result  # Table borders
        assert "|" in result  # Column separators

    def test_build_ascii_table_column_widths(self):
        """Test that columns are properly sized."""
        headers = ["Short", "LongerHeader"]
        rows = [["a", "b"]]
        result = _build_ascii_table(headers, rows)

        lines = result.split("\n")
        # All lines with content should have same length
        content_lines = [l for l in lines if l.startswith("|") or l.startswith("+")]
        lengths = [len(l) for l in content_lines]
        assert len(set(lengths)) == 1  # All same length

    def test_build_ascii_table_empty_rows(self):
        """Test table with no data rows."""
        headers = ["Col1", "Col2"]
        rows = []
        result = _build_ascii_table(headers, rows)

        assert "Col1" in result
        assert "Col2" in result


# --- Format Search Results Tests ---


class TestFormatSearchResultsText:
    """Tests for search results formatting in text format."""

    def test_format_search_results_text_basic(self):
        """Test basic text formatting of search results."""
        node = Node(type="task", content="Implement login")
        results = [(node, 0.92)]

        output = format_search_results(results, output_format="text")

        assert "Found 1 result(s)" in output
        assert "[task]" in output
        assert "Implement login" in output
        assert "0.92" in output

    def test_format_search_results_text_multiple(self):
        """Test text formatting of multiple results."""
        node1 = Node(type="task", content="Task 1")
        node2 = Node(type="decision", content="Decision 1")
        results = [(node1, 0.95), (node2, 0.85)]

        output = format_search_results(results, output_format="text")

        assert "Found 2 result(s)" in output
        assert "[task]" in output
        assert "[decision]" in output
        assert "Task 1" in output
        assert "Decision 1" in output

    def test_format_search_results_text_with_source(self):
        """Test text formatting includes source attribution."""
        node = Node(type="task", content="Test", metadata={"session_id": "sess-123"})
        results = [(node, 0.9)]

        output = format_search_results(results, output_format="text")

        assert "Source: session:sess-123" in output

    def test_format_search_results_text_hide_score(self):
        """Test hiding score in text format."""
        node = Node(type="task", content="Test")
        results = [(node, 0.92)]

        output = format_search_results(results, output_format="text", show_score=False)

        assert "0.92" not in output
        assert "score" not in output.lower()

    def test_format_search_results_text_verbose(self):
        """Test verbose text formatting."""
        node = Node(type="task", content="Test", metadata={"priority": "high"})
        results = [(node, 0.9)]

        output = format_search_results(results, output_format="text", verbose=True)

        assert "UUID:" in output
        assert "Created:" in output
        assert "priority: high" in output

    def test_format_search_results_text_empty(self):
        """Test text formatting of empty results."""
        output = format_search_results([], output_format="text")

        assert "No search results found." in output


class TestFormatSearchResultsJson:
    """Tests for search results formatting in JSON format."""

    def test_format_search_results_json_basic(self):
        """Test basic JSON formatting of search results."""
        node = Node(type="task", content="Test task")
        results = [(node, 0.9)]

        output = format_search_results(results, output_format="json")
        data = json.loads(output)

        assert data["count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["type"] == "task"
        assert data["results"][0]["content"] == "Test task"
        assert data["results"][0]["score"] == 0.9

    def test_format_search_results_json_hide_score(self):
        """Test JSON format without score."""
        node = Node(type="task", content="Test")
        results = [(node, 0.9)]

        output = format_search_results(results, output_format="json", show_score=False)
        data = json.loads(output)

        assert "score" not in data["results"][0]

    def test_format_search_results_json_with_source(self):
        """Test JSON format includes source."""
        node = Node(type="task", content="Test", metadata={"project_id": "proj-123"})
        results = [(node, 0.9)]

        output = format_search_results(results, output_format="json")
        data = json.loads(output)

        assert data["results"][0]["source"] == "project:proj-123"

    def test_format_search_results_json_empty(self):
        """Test JSON formatting of empty results."""
        output = format_search_results([], output_format="json")
        data = json.loads(output)

        assert data["count"] == 0
        assert data["results"] == []


class TestFormatSearchResultsTable:
    """Tests for search results formatting in table format."""

    def test_format_search_results_table_basic(self):
        """Test basic table formatting of search results."""
        node = Node(type="task", content="Test task")
        results = [(node, 0.9)]

        output = format_search_results(results, output_format="table")

        assert "#" in output
        assert "Type" in output
        assert "Content" in output
        assert "Score" in output
        assert "task" in output

    def test_format_search_results_table_with_source(self):
        """Test table format includes source column when available."""
        node = Node(type="task", content="Test", metadata={"session_id": "sess-123"})
        results = [(node, 0.9)]

        output = format_search_results(results, output_format="table")

        assert "Source" in output
        # Source may be truncated in table format, so check for prefix
        assert "session:" in output

    def test_format_search_results_table_hide_score(self):
        """Test table format without score column."""
        node = Node(type="task", content="Test")
        results = [(node, 0.9)]

        output = format_search_results(results, output_format="table", show_score=False)

        # Score column header should not appear
        lines = output.split("\n")
        header_line = [l for l in lines if "Type" in l][0]
        assert "Score" not in header_line

    def test_format_search_results_table_empty(self):
        """Test table formatting of empty results."""
        output = format_search_results([], output_format="table")

        assert "No search results found." in output


# --- Format Node Tests ---


class TestFormatNodeText:
    """Tests for single node formatting in text format."""

    def test_format_node_text_basic(self):
        """Test basic node text formatting."""
        node = Node(type="decision", content="Use JWT for auth")

        output = format_node(node, output_format="text")

        assert "[decision]" in output
        assert "Use JWT for auth" in output
        assert "UUID:" in output
        assert "Created:" in output
        assert "Updated:" in output

    def test_format_node_text_verbose(self):
        """Test verbose node text formatting."""
        node = Node(type="task", content="Test", metadata={"priority": "high", "assignee": "dev"})

        output = format_node(node, output_format="text", verbose=True)

        assert "Metadata:" in output
        assert "priority: high" in output
        assert "assignee: dev" in output


class TestFormatNodeJson:
    """Tests for single node formatting in JSON format."""

    def test_format_node_json_basic(self):
        """Test basic node JSON formatting."""
        node = Node(type="task", content="Test task")

        output = format_node(node, output_format="json")
        data = json.loads(output)

        assert data["type"] == "task"
        assert data["content"] == "Test task"
        assert "uuid" in data

    def test_format_node_json_verbose(self):
        """Test verbose node JSON formatting includes metadata."""
        node = Node(type="task", content="Test", metadata={"status": "done"})

        output = format_node(node, output_format="json", verbose=True)
        data = json.loads(output)

        assert "metadata" in data
        assert data["metadata"]["status"] == "done"


class TestFormatNodeTable:
    """Tests for single node formatting in table format."""

    def test_format_node_table_basic(self):
        """Test basic node table formatting."""
        node = Node(type="task", content="Test task")

        output = format_node(node, output_format="table")

        assert "Field" in output
        assert "Value" in output
        assert "Type" in output
        assert "task" in output


# --- Format Tasks Tests ---


class TestFormatTasksText:
    """Tests for tasks formatting in text format."""

    def test_format_tasks_text_basic(self):
        """Test basic tasks text formatting."""
        task1 = Node(type="task", content="Implement login", metadata={"status": "completed"})
        task2 = Node(type="task", content="Write tests", metadata={"status": "pending"})
        tasks = [task1, task2]

        output = format_tasks(tasks, output_format="text")

        assert "Tasks (2 total)" in output
        assert "[x] Implement login" in output
        assert "[ ] Write tests" in output

    def test_format_tasks_text_in_progress(self):
        """Test tasks formatting shows in-progress status."""
        task = Node(type="task", content="Working on it", metadata={"status": "in_progress"})

        output = format_tasks([task], output_format="text")

        assert "[-] Working on it" in output

    def test_format_tasks_text_verbose(self):
        """Test verbose tasks text formatting."""
        task = Node(
            type="task",
            content="Test",
            metadata={"status": "pending", "priority": "high"}
        )

        output = format_tasks([task], output_format="text", verbose=True)

        assert "Status: pending" in output
        assert "UUID:" in output
        assert "priority: high" in output

    def test_format_tasks_text_empty(self):
        """Test empty tasks text formatting."""
        output = format_tasks([], output_format="text")

        assert "No tasks found." in output


class TestFormatTasksJson:
    """Tests for tasks formatting in JSON format."""

    def test_format_tasks_json_basic(self):
        """Test basic tasks JSON formatting."""
        task = Node(type="task", content="Test task", metadata={"status": "completed"})

        output = format_tasks([task], output_format="json")
        data = json.loads(output)

        assert data["count"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["status"] == "completed"

    def test_format_tasks_json_empty(self):
        """Test empty tasks JSON formatting."""
        output = format_tasks([], output_format="json")
        data = json.loads(output)

        assert data["count"] == 0
        assert data["results"] == []


class TestFormatTasksTable:
    """Tests for tasks formatting in table format."""

    def test_format_tasks_table_basic(self):
        """Test basic tasks table formatting."""
        task = Node(type="task", content="Test task", metadata={"status": "pending"})

        output = format_tasks([task], output_format="table")

        assert "Status" in output
        assert "Task" in output
        assert "Created" in output
        assert "[ ]" in output

    def test_format_tasks_table_empty(self):
        """Test empty tasks table formatting."""
        output = format_tasks([], output_format="table")

        assert "No tasks found." in output


# --- Format Decisions Tests ---


class TestFormatDecisionsText:
    """Tests for decisions formatting in text format."""

    def test_format_decisions_text_basic(self):
        """Test basic decisions text formatting."""
        decision = Node(
            type="decision",
            content="Use JWT for authentication",
            metadata={"rationale": "Stateless and scalable"}
        )

        output = format_decisions([decision], output_format="text")

        assert "Decisions (1 total)" in output
        assert "1. Use JWT for authentication" in output
        assert "Rationale: Stateless and scalable" in output
        assert "Made:" in output

    def test_format_decisions_text_with_source(self):
        """Test decisions text formatting includes source."""
        decision = Node(
            type="decision",
            content="Use PostgreSQL",
            metadata={"session_id": "sess-123"}
        )

        output = format_decisions([decision], output_format="text")

        assert "Source: session:sess-123" in output

    def test_format_decisions_text_no_rationale(self):
        """Test decisions formatting without rationale."""
        decision = Node(type="decision", content="Use PostgreSQL")

        output = format_decisions([decision], output_format="text")

        assert "Use PostgreSQL" in output
        assert "Rationale:" not in output

    def test_format_decisions_text_verbose(self):
        """Test verbose decisions text formatting."""
        decision = Node(
            type="decision",
            content="Use JWT",
            metadata={"rationale": "Scalable", "team": "backend"}
        )

        output = format_decisions([decision], output_format="text", verbose=True)

        assert "UUID:" in output
        assert "team: backend" in output

    def test_format_decisions_text_empty(self):
        """Test empty decisions text formatting."""
        output = format_decisions([], output_format="text")

        assert "No decisions found." in output


class TestFormatDecisionsJson:
    """Tests for decisions formatting in JSON format."""

    def test_format_decisions_json_basic(self):
        """Test basic decisions JSON formatting."""
        decision = Node(
            type="decision",
            content="Use JWT",
            metadata={"rationale": "Scalable"}
        )

        output = format_decisions([decision], output_format="json")
        data = json.loads(output)

        assert data["count"] == 1
        assert len(data["decisions"]) == 1
        assert data["decisions"][0]["rationale"] == "Scalable"

    def test_format_decisions_json_no_rationale(self):
        """Test decisions JSON without rationale field."""
        decision = Node(type="decision", content="Use PostgreSQL")

        output = format_decisions([decision], output_format="json")
        data = json.loads(output)

        assert "rationale" not in data["decisions"][0]

    def test_format_decisions_json_empty(self):
        """Test empty decisions JSON formatting."""
        output = format_decisions([], output_format="json")
        data = json.loads(output)

        assert data["count"] == 0
        assert data["results"] == []


class TestFormatDecisionsTable:
    """Tests for decisions formatting in table format."""

    def test_format_decisions_table_basic(self):
        """Test basic decisions table formatting."""
        decision = Node(
            type="decision",
            content="Use JWT",
            metadata={"rationale": "Scalable"}
        )

        output = format_decisions([decision], output_format="table")

        assert "#" in output
        assert "Decision" in output
        assert "Rationale" in output
        assert "Date" in output

    def test_format_decisions_table_empty(self):
        """Test empty decisions table formatting."""
        output = format_decisions([], output_format="table")

        assert "No decisions found." in output


# --- Format Recent Tests ---


class TestFormatRecentText:
    """Tests for recent items formatting in text format."""

    def test_format_recent_text_basic(self):
        """Test basic recent items text formatting."""
        item1 = Node(type="task", content="Implement login")
        item2 = Node(type="decision", content="Use JWT")
        items = [item1, item2]

        output = format_recent(items, output_format="text")

        assert "Recent Activity (2 items)" in output
        assert "[task]" in output
        assert "[decision]" in output
        assert "Implement login" in output
        assert "Use JWT" in output

    def test_format_recent_text_shows_time(self):
        """Test recent items show time in HH:MM format."""
        now = datetime.now()
        item = Node(type="task", content="Test")
        item.created_at = now

        output = format_recent([item], output_format="text")

        expected_time = now.strftime("%H:%M")
        assert f"[{expected_time}]" in output

    def test_format_recent_text_verbose(self):
        """Test verbose recent items text formatting."""
        item = Node(type="task", content="Test", metadata={"priority": "high"})

        output = format_recent([item], output_format="text", verbose=True)

        assert "UUID:" in output
        assert "Date:" in output
        assert "priority: high" in output

    def test_format_recent_text_empty(self):
        """Test empty recent items text formatting."""
        output = format_recent([], output_format="text")

        assert "No recent items found." in output


class TestFormatRecentJson:
    """Tests for recent items formatting in JSON format."""

    def test_format_recent_json_basic(self):
        """Test basic recent items JSON formatting."""
        item = Node(type="session", content="Work session")

        output = format_recent([item], output_format="json")
        data = json.loads(output)

        assert data["count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["type"] == "session"

    def test_format_recent_json_empty(self):
        """Test empty recent items JSON formatting."""
        output = format_recent([], output_format="json")
        data = json.loads(output)

        assert data["count"] == 0
        assert data["results"] == []


class TestFormatRecentTable:
    """Tests for recent items formatting in table format."""

    def test_format_recent_table_basic(self):
        """Test basic recent items table formatting."""
        item = Node(type="task", content="Test task", metadata={"session_id": "sess-123"})

        output = format_recent([item], output_format="table")

        assert "Time" in output
        assert "Type" in output
        assert "Content" in output
        assert "Source" in output

    def test_format_recent_table_empty(self):
        """Test empty recent items table formatting."""
        output = format_recent([], output_format="table")

        assert "No recent items found." in output


# --- Integration Tests ---


class TestFormatterIntegration:
    """Integration tests for formatters."""

    def test_all_formatters_handle_empty_input(self):
        """Test all formatters handle empty input gracefully."""
        assert "No" in format_search_results([])
        assert "No" in format_tasks([])
        assert "No" in format_decisions([])
        assert "No" in format_recent([])

    def test_all_formatters_support_all_formats(self):
        """Test all formatters support text, json, and table formats."""
        node = Node(type="task", content="Test", metadata={"status": "pending"})
        results = [(node, 0.9)]

        for fmt in ["text", "json", "table"]:
            # Should not raise
            format_search_results(results, output_format=fmt)
            format_node(node, output_format=fmt)
            format_tasks([node], output_format=fmt)
            format_decisions([node], output_format=fmt)
            format_recent([node], output_format=fmt)

    def test_json_output_is_valid_json(self):
        """Test that JSON outputs are valid JSON."""
        node = Node(type="task", content="Test", metadata={"key": "value"})

        # All should parse without error
        json.loads(format_search_results([(node, 0.9)], output_format="json"))
        json.loads(format_node(node, output_format="json"))
        json.loads(format_tasks([node], output_format="json"))
        json.loads(format_decisions([node], output_format="json"))
        json.loads(format_recent([node], output_format="json"))

    def test_text_output_is_readable(self):
        """Test that text outputs are human readable."""
        node = Node(type="task", content="Implement feature X")

        text_output = format_search_results([(node, 0.95)], output_format="text")

        # Should contain meaningful text
        assert len(text_output) > 50
        assert "task" in text_output.lower()
        assert "Implement feature X" in text_output

    def test_table_output_has_structure(self):
        """Test that table outputs have proper structure."""
        node = Node(type="task", content="Test")

        table_output = format_search_results([(node, 0.9)], output_format="table")

        # Should have table structure
        assert "|" in table_output
        assert "+" in table_output

    def test_long_content_truncation(self):
        """Test that long content is properly truncated."""
        long_content = "A" * 200
        node = Node(type="task", content=long_content)

        # Text format truncates
        text_output = format_search_results([(node, 0.9)], output_format="text", verbose=False)
        assert "..." in text_output

        # JSON preserves full content
        json_output = format_search_results([(node, 0.9)], output_format="json")
        data = json.loads(json_output)
        assert data["results"][0]["content"] == long_content

    def test_special_characters_in_content(self):
        """Test handling of special characters in content."""
        node = Node(type="task", content='Test with "quotes" and <brackets>')

        # Should not raise
        format_search_results([(node, 0.9)], output_format="text")
        format_search_results([(node, 0.9)], output_format="json")
        format_search_results([(node, 0.9)], output_format="table")

    def test_unicode_content(self):
        """Test handling of unicode content."""
        node = Node(type="task", content="Test with emoji 🚀 and unicode ñ")

        # Should not raise
        text_output = format_search_results([(node, 0.9)], output_format="text")
        assert "🚀" in text_output
        assert "ñ" in text_output
