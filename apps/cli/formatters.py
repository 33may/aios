"""
Output Formatters for CLI

Provides formatting functions for displaying query results from the knowledge graph.
Supports multiple output formats (text, json, table) and specialized formatters
for different node types (tasks, decisions, sessions).
"""

from dataclasses import asdict
from datetime import datetime
from typing import List, Optional, Tuple
import json

from apps.backend.integrations.graphiti.models import Node


def format_search_results(
    results: List[Tuple[Node, float]],
    output_format: str = "text",
    show_score: bool = True,
    verbose: bool = False
) -> str:
    """
    Format search results for display.

    Takes a list of (Node, score) tuples from semantic search and formats
    them for terminal output with source attribution.

    Args:
        results: List of (Node, score) tuples from search
        output_format: Output format ("text", "json", or "table")
        show_score: Whether to show relevance scores
        verbose: Whether to show detailed node information

    Returns:
        Formatted string representation of the search results.

    Example:
        >>> results = engine.search("authentication")
        >>> print(format_search_results(results))
        [decision] Use JWT for authentication (score: 0.92)
          Created: 2024-01-15 10:30:00
    """
    if not results:
        return _format_empty_results(output_format, "search results")

    if output_format == "json":
        return _format_search_results_json(results, show_score, verbose)
    elif output_format == "table":
        return _format_search_results_table(results, show_score, verbose)
    else:
        return _format_search_results_text(results, show_score, verbose)


def format_node(
    node: Node,
    output_format: str = "text",
    verbose: bool = False
) -> str:
    """
    Format a single node for display.

    Renders a knowledge graph node with its type, content, and metadata
    in the specified output format.

    Args:
        node: The Node object to format
        output_format: Output format ("text", "json", or "table")
        verbose: Whether to show detailed node information

    Returns:
        Formatted string representation of the node.

    Example:
        >>> print(format_node(node))
        [decision] Use JWT for authentication
          UUID: abc123
          Created: 2024-01-15 10:30:00
    """
    if output_format == "json":
        return _format_node_json(node, verbose)
    elif output_format == "table":
        return _format_node_table(node, verbose)
    else:
        return _format_node_text(node, verbose)


def format_tasks(
    tasks: List[Node],
    output_format: str = "text",
    verbose: bool = False
) -> str:
    """
    Format a list of task nodes for display.

    Renders task nodes with their status, content, and metadata
    in a format optimized for task lists.

    Args:
        tasks: List of task Node objects
        output_format: Output format ("text", "json", or "table")
        verbose: Whether to show detailed task information

    Returns:
        Formatted string representation of the tasks.

    Example:
        >>> print(format_tasks(tasks))
        Tasks (3 total):
        [ ] Implement user login
        [x] Create database schema
        [ ] Write unit tests
    """
    if not tasks:
        return _format_empty_results(output_format, "tasks")

    if output_format == "json":
        return _format_tasks_json(tasks, verbose)
    elif output_format == "table":
        return _format_tasks_table(tasks, verbose)
    else:
        return _format_tasks_text(tasks, verbose)


def format_decisions(
    decisions: List[Node],
    output_format: str = "text",
    verbose: bool = False
) -> str:
    """
    Format a list of decision nodes for display.

    Renders decision nodes with their rationale, context, and metadata
    in a format optimized for decision history.

    Args:
        decisions: List of decision Node objects
        output_format: Output format ("text", "json", or "table")
        verbose: Whether to show detailed decision information

    Returns:
        Formatted string representation of the decisions.

    Example:
        >>> print(format_decisions(decisions))
        Decisions (2 total):

        1. Use JWT for authentication
           Rationale: Stateless, scalable, industry standard
           Made: 2024-01-15 10:30:00

        2. Choose PostgreSQL over MongoDB
           Rationale: Strong ACID compliance, better for relational data
           Made: 2024-01-14 14:20:00
    """
    if not decisions:
        return _format_empty_results(output_format, "decisions")

    if output_format == "json":
        return _format_decisions_json(decisions, verbose)
    elif output_format == "table":
        return _format_decisions_table(decisions, verbose)
    else:
        return _format_decisions_text(decisions, verbose)


def format_recent(
    items: List[Node],
    output_format: str = "text",
    verbose: bool = False
) -> str:
    """
    Format a list of recent items (any node type) for display.

    Renders a mixed list of recent nodes sorted by time, showing
    the type, content, and timestamp for each item.

    Args:
        items: List of Node objects (any type), typically sorted by recency
        output_format: Output format ("text", "json", or "table")
        verbose: Whether to show detailed item information

    Returns:
        Formatted string representation of recent items.

    Example:
        >>> print(format_recent(items))
        Recent Activity (5 items):

        [10:30] [task] Implement user login
        [10:25] [decision] Use JWT for authentication
        [10:20] [session] Started work on auth module
        [10:15] [task] Create database schema
        [10:10] [note] Need to review security requirements
    """
    if not items:
        return _format_empty_results(output_format, "recent items")

    if output_format == "json":
        return _format_recent_json(items, verbose)
    elif output_format == "table":
        return _format_recent_table(items, verbose)
    else:
        return _format_recent_text(items, verbose)


# --- Private helper functions ---


def _format_empty_results(output_format: str, result_type: str) -> str:
    """Format empty results message."""
    if output_format == "json":
        return json.dumps({"results": [], "count": 0}, indent=2)
    elif output_format == "table":
        return f"No {result_type} found."
    else:
        return f"No {result_type} found."


def _format_timestamp(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _truncate_content(content: str, max_length: int = 80) -> str:
    """Truncate content to max length with ellipsis."""
    if len(content) <= max_length:
        return content
    return content[:max_length - 3] + "..."


def _get_task_status(node: Node) -> str:
    """Extract task status from node metadata."""
    if node.metadata:
        status = node.metadata.get("status", "pending")
        return status
    return "pending"


def _get_task_checkbox(node: Node) -> str:
    """Get checkbox representation for task status."""
    status = _get_task_status(node)
    if status in ("completed", "done", "finished"):
        return "[x]"
    elif status in ("in_progress", "active", "working"):
        return "[-]"
    else:
        return "[ ]"


def _get_decision_rationale(node: Node) -> Optional[str]:
    """Extract rationale from decision node metadata."""
    if not node.metadata:
        return None

    # Try different field names for rationale
    rationale_fields = ["rationale", "reason", "why", "justification", "explanation"]
    for field in rationale_fields:
        if field in node.metadata:
            value = node.metadata[field]
            if value:
                return str(value)

    return None


def _get_source_attribution(node: Node) -> Optional[str]:
    """
    Extract source attribution from node metadata.

    Source attribution indicates where the knowledge originated from,
    such as a session, project, file, or other context.

    Args:
        node: The Node to extract source from

    Returns:
        Source attribution string, or None if no source info available
    """
    if not node.metadata:
        return None

    # Priority order for source attribution
    source_fields = [
        ("session_id", "session"),
        ("session", "session"),
        ("project_id", "project"),
        ("project", "project"),
        ("source_file", "file"),
        ("source", None),  # Use value directly
        ("file", "file"),
        ("origin", None),  # Use value directly
    ]

    for field, prefix in source_fields:
        if field in node.metadata:
            value = node.metadata[field]
            if value:
                if prefix:
                    return f"{prefix}:{value}"
                return str(value)

    return None


def _format_source_line(node: Node) -> str:
    """Format source attribution as a display line."""
    source = _get_source_attribution(node)
    if source:
        return f"   Source: {source}"
    return ""


# --- Text format implementations ---


def _format_search_results_text(
    results: List[Tuple[Node, float]],
    show_score: bool,
    verbose: bool
) -> str:
    """Format search results as plain text with source attribution."""
    lines = []
    lines.append(f"Found {len(results)} result(s):\n")

    for i, (node, score) in enumerate(results, 1):
        score_str = f" (score: {score:.2f})" if show_score else ""
        type_str = f"[{node.type}]"
        content = _truncate_content(node.content) if not verbose else node.content

        lines.append(f"{i}. {type_str} {content}{score_str}")

        # Always show source attribution when available
        source_line = _format_source_line(node)
        if source_line:
            lines.append(source_line)

        if verbose:
            lines.append(f"   UUID: {node.uuid}")
            lines.append(f"   Created: {_format_timestamp(node.created_at)}")
            if node.metadata:
                # Show metadata fields except those already shown as source
                source_fields = {"session_id", "session", "project_id", "project",
                               "source_file", "source", "file", "origin"}
                for key, value in node.metadata.items():
                    if key not in source_fields:
                        lines.append(f"   {key}: {value}")
        lines.append("")

    return "\n".join(lines).strip()


def _format_node_text(node: Node, verbose: bool) -> str:
    """Format a single node as plain text."""
    lines = []
    type_str = f"[{node.type}]"
    content = node.content if verbose else _truncate_content(node.content)

    lines.append(f"{type_str} {content}")
    lines.append(f"  UUID: {node.uuid}")
    lines.append(f"  Created: {_format_timestamp(node.created_at)}")
    lines.append(f"  Updated: {_format_timestamp(node.updated_at)}")

    if verbose and node.metadata:
        lines.append("  Metadata:")
        for key, value in node.metadata.items():
            lines.append(f"    {key}: {value}")

    return "\n".join(lines)


def _format_tasks_text(tasks: List[Node], verbose: bool) -> str:
    """Format tasks as plain text list."""
    lines = []
    lines.append(f"Tasks ({len(tasks)} total):\n")

    for task in tasks:
        checkbox = _get_task_checkbox(task)
        content = _truncate_content(task.content, 60) if not verbose else task.content
        lines.append(f"{checkbox} {content}")

        if verbose:
            status = _get_task_status(task)
            lines.append(f"    Status: {status}")
            lines.append(f"    UUID: {task.uuid}")
            lines.append(f"    Created: {_format_timestamp(task.created_at)}")
            if task.metadata:
                for key, value in task.metadata.items():
                    if key != "status":
                        lines.append(f"    {key}: {value}")

    return "\n".join(lines)


def _format_decisions_text(decisions: List[Node], verbose: bool) -> str:
    """Format decisions as plain text list."""
    lines = []
    lines.append(f"Decisions ({len(decisions)} total):\n")

    for i, decision in enumerate(decisions, 1):
        content = _truncate_content(decision.content, 70) if not verbose else decision.content
        lines.append(f"{i}. {content}")

        # Show rationale if available
        rationale = _get_decision_rationale(decision)
        if rationale:
            rationale_display = rationale if verbose else _truncate_content(rationale, 60)
            lines.append(f"   Rationale: {rationale_display}")

        lines.append(f"   Made: {_format_timestamp(decision.created_at)}")

        # Show source attribution
        source_line = _format_source_line(decision)
        if source_line:
            lines.append(source_line)

        if verbose:
            lines.append(f"   UUID: {decision.uuid}")
            if decision.metadata:
                for key, value in decision.metadata.items():
                    if key not in ("rationale", "reason", "why"):
                        lines.append(f"   {key}: {value}")

        lines.append("")  # Blank line between decisions

    return "\n".join(lines).strip()


def _format_recent_text(items: List[Node], verbose: bool) -> str:
    """Format recent items as plain text list."""
    lines = []
    lines.append(f"Recent Activity ({len(items)} items):\n")

    for item in items:
        # Format time as HH:MM
        time_str = item.created_at.strftime("%H:%M") if item.created_at else "??:??"
        type_str = f"[{item.type}]"
        content = _truncate_content(item.content, 50) if not verbose else item.content

        lines.append(f"[{time_str}] {type_str} {content}")

        if verbose:
            lines.append(f"         UUID: {item.uuid}")
            lines.append(f"         Date: {_format_timestamp(item.created_at)}")
            source_line = _format_source_line(item)
            if source_line:
                lines.append(f"        {source_line.strip()}")
            if item.metadata:
                for key, value in item.metadata.items():
                    lines.append(f"         {key}: {value}")
            lines.append("")

    return "\n".join(lines).strip()


# --- JSON format implementations ---


def _format_search_results_json(
    results: List[Tuple[Node, float]],
    show_score: bool,
    verbose: bool
) -> str:
    """Format search results as JSON."""
    items = []
    for node, score in results:
        item = _node_to_dict(node, verbose)
        if show_score:
            item["score"] = round(score, 4)
        items.append(item)

    output = {
        "count": len(results),
        "results": items
    }
    return json.dumps(output, indent=2, default=str)


def _format_node_json(node: Node, verbose: bool) -> str:
    """Format a single node as JSON."""
    data = _node_to_dict(node, verbose)
    return json.dumps(data, indent=2, default=str)


def _format_tasks_json(tasks: List[Node], verbose: bool) -> str:
    """Format tasks as JSON."""
    items = []
    for task in tasks:
        item = _node_to_dict(task, verbose)
        item["status"] = _get_task_status(task)
        items.append(item)

    output = {
        "count": len(tasks),
        "tasks": items
    }
    return json.dumps(output, indent=2, default=str)


def _format_decisions_json(decisions: List[Node], verbose: bool) -> str:
    """Format decisions as JSON."""
    items = []
    for decision in decisions:
        item = _node_to_dict(decision, verbose)
        rationale = _get_decision_rationale(decision)
        if rationale:
            item["rationale"] = rationale
        items.append(item)

    output = {
        "count": len(decisions),
        "decisions": items
    }
    return json.dumps(output, indent=2, default=str)


def _format_recent_json(items: List[Node], verbose: bool) -> str:
    """Format recent items as JSON."""
    result_items = []
    for item in items:
        item_dict = _node_to_dict(item, verbose)
        result_items.append(item_dict)

    output = {
        "count": len(items),
        "items": result_items
    }
    return json.dumps(output, indent=2, default=str)


def _node_to_dict(node: Node, verbose: bool) -> dict:
    """Convert node to dictionary for JSON serialization with source attribution."""
    data = {
        "type": node.type,
        "content": node.content,
        "uuid": node.uuid,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
    }
    # Always include source attribution when available
    source = _get_source_attribution(node)
    if source:
        data["source"] = source
    if verbose and node.metadata:
        data["metadata"] = node.metadata
    return data


# --- Table format implementations ---


def _format_search_results_table(
    results: List[Tuple[Node, float]],
    show_score: bool,
    verbose: bool
) -> str:
    """Format search results as ASCII table with source attribution."""
    # Check if any results have source attribution
    has_source = any(_get_source_attribution(node) for node, _ in results)

    if show_score:
        if has_source:
            headers = ["#", "Type", "Content", "Source", "Score"]
            rows = []
            for i, (node, score) in enumerate(results, 1):
                content = _truncate_content(node.content, 40)
                source = _get_source_attribution(node) or "-"
                source = _truncate_content(source, 15)
                rows.append([str(i), node.type, content, source, f"{score:.2f}"])
        else:
            headers = ["#", "Type", "Content", "Score"]
            rows = []
            for i, (node, score) in enumerate(results, 1):
                content = _truncate_content(node.content, 50)
                rows.append([str(i), node.type, content, f"{score:.2f}"])
    else:
        if has_source:
            headers = ["#", "Type", "Content", "Source"]
            rows = []
            for i, (node, _score) in enumerate(results, 1):
                content = _truncate_content(node.content, 45)
                source = _get_source_attribution(node) or "-"
                source = _truncate_content(source, 15)
                rows.append([str(i), node.type, content, source])
        else:
            headers = ["#", "Type", "Content"]
            rows = []
            for i, (node, _score) in enumerate(results, 1):
                content = _truncate_content(node.content, 60)
                rows.append([str(i), node.type, content])

    return _build_ascii_table(headers, rows)


def _format_node_table(node: Node, verbose: bool) -> str:
    """Format a single node as ASCII table."""
    headers = ["Field", "Value"]
    rows = [
        ["Type", node.type],
        ["Content", _truncate_content(node.content, 60) if not verbose else node.content],
        ["UUID", node.uuid],
        ["Created", _format_timestamp(node.created_at)],
        ["Updated", _format_timestamp(node.updated_at)],
    ]
    if verbose and node.metadata:
        for key, value in node.metadata.items():
            rows.append([key, str(value)])

    return _build_ascii_table(headers, rows)


def _format_tasks_table(tasks: List[Node], verbose: bool) -> str:
    """Format tasks as ASCII table."""
    headers = ["Status", "Task", "Created"]
    rows = []
    for task in tasks:
        checkbox = _get_task_checkbox(task)
        content = _truncate_content(task.content, 50)
        created = _format_timestamp(task.created_at)
        rows.append([checkbox, content, created])

    return _build_ascii_table(headers, rows)


def _format_decisions_table(decisions: List[Node], verbose: bool) -> str:
    """Format decisions as ASCII table."""
    headers = ["#", "Decision", "Rationale", "Date"]
    rows = []
    for i, decision in enumerate(decisions, 1):
        content = _truncate_content(decision.content, 35)
        rationale = _get_decision_rationale(decision) or "-"
        rationale = _truncate_content(rationale, 25)
        date = decision.created_at.strftime("%Y-%m-%d") if decision.created_at else "-"
        rows.append([str(i), content, rationale, date])

    return _build_ascii_table(headers, rows)


def _format_recent_table(items: List[Node], verbose: bool) -> str:
    """Format recent items as ASCII table."""
    headers = ["Time", "Type", "Content", "Source"]
    rows = []
    for item in items:
        time_str = item.created_at.strftime("%H:%M") if item.created_at else "??:??"
        content = _truncate_content(item.content, 40)
        source = _get_source_attribution(item) or "-"
        source = _truncate_content(source, 15)
        rows.append([time_str, item.type, content, source])

    return _build_ascii_table(headers, rows)


def _build_ascii_table(headers: List[str], rows: List[List[str]]) -> str:
    """Build a simple ASCII table."""
    # Calculate column widths
    all_rows = [headers] + rows
    col_widths = []
    for col_idx in range(len(headers)):
        max_width = max(len(str(row[col_idx])) for row in all_rows)
        col_widths.append(max_width)

    # Build separator line
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    # Build header row
    header_cells = [f" {headers[i].ljust(col_widths[i])} " for i in range(len(headers))]
    header_line = "|" + "|".join(header_cells) + "|"

    # Build data rows
    lines = [separator, header_line, separator]
    for row in rows:
        cells = [f" {str(row[i]).ljust(col_widths[i])} " for i in range(len(row))]
        lines.append("|" + "|".join(cells) + "|")
    lines.append(separator)

    return "\n".join(lines)
