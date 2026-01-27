"""
MCP Server for Knowledge Graph Integration

Exposes the Graphiti knowledge graph to Claude Code via Model Context Protocol,
enabling Claude to act as a project manager with persistent memory about
decisions, tasks, context, and project history.

Usage:
    python -m apps.mcp.knowledge_server

Configuration:
    Set in ~/.claude.json or project .mcp.json:
    {
        "mcpServers": {
            "knowledge": {
                "command": "python",
                "args": ["-m", "apps.mcp.knowledge_server"],
                "cwd": "/path/to/management_agent"
            }
        }
    }
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Sequence

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.mcp.tools.search import search_knowledge, get_project_context
from apps.mcp.tools.decisions import get_decisions, record_decision
from apps.mcp.tools.tasks import get_tasks, add_task, update_task, delete_task
from apps.mcp.tools.activity import get_recent_activity, add_discovery, add_thought, add_problem, add_fix
from apps.mcp.tools.traversal import traverse_related, link_nodes
from apps.mcp.tools.session import initialize_session
from apps.mcp.tools.context import (
    get_context,
    set_context,
    create_project,
    list_projects,
    get_task_tree,
    add_constraint,
    set_focus,
    clear_focus,
    get_reasoning_context,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("knowledge-graph")

# Global client instance (initialized on startup)
_client: GraphitiClient | None = None


def get_client() -> GraphitiClient:
    """Get or create the Graphiti client."""
    global _client
    if _client is None:
        _client = GraphitiClient()
        _client.connect()
        logger.info("Initialized Graphiti client")
    return _client


# Tool definitions with JSON schemas
TOOLS = [
    Tool(
        name="search_knowledge",
        description="Semantic search across all knowledge in the graph. Use this to find relevant context, past decisions, discoveries, or any information by natural language query.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                    "default": 10,
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum relevance score threshold (0.0-1.0)",
                    "default": 0.0,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_decisions",
        description="Retrieve architectural and design decisions. Use this to understand why certain choices were made, what alternatives were considered, and the rationale behind decisions.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to scope decisions",
                },
                "days": {
                    "type": "integer",
                    "description": "How far back to look (default: 90 days)",
                    "default": 90,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of decisions (default: 20)",
                    "default": 20,
                },
            },
        },
    ),
    Tool(
        name="get_tasks",
        description="Retrieve tasks from the knowledge graph. Use this to see what work is pending, in progress, completed, or blocked. Supports hierarchical filtering by parent_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: pending, in_progress, completed, blocked",
                    "enum": ["pending", "in_progress", "completed", "blocked"],
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to scope tasks",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Optional parent task ID to get subtasks of",
                },
                "top_level_only": {
                    "type": "boolean",
                    "description": "If true, only return tasks without a parent (depth 0)",
                    "default": False,
                },
                "days": {
                    "type": "integer",
                    "description": "How far back to look (default: 30 days)",
                    "default": 30,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tasks (default: 20)",
                    "default": 20,
                },
            },
        },
    ),
    Tool(
        name="get_recent_activity",
        description="Get recent activity feed across all node types. Use this to see what has been happening in the project recently.",
        inputSchema={
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "How far back to look in hours (default: 24)",
                    "default": 24,
                },
                "types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by node types: decision, task, discovery, session",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 50)",
                    "default": 50,
                },
            },
        },
    ),
    Tool(
        name="record_decision",
        description="Record a new architectural or design decision. When use_context=true (default), links to focus via 'led_to', auto-links all collected constraints via 'constrained_by', and becomes new focus.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title for the decision",
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this choice was made",
                },
                "alternatives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What other options were considered",
                },
                "context": {
                    "type": "string",
                    "description": "What prompted this decision",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to associate with",
                },
                "use_context": {
                    "type": "boolean",
                    "description": "If true (default), auto-link to focus, constraints, and become new focus",
                    "default": True,
                },
                "parent_id": {
                    "type": "string",
                    "description": "Explicit parent node ID (overrides current focus)",
                },
            },
            "required": ["title", "rationale"],
        },
    ),
    Tool(
        name="add_task",
        description="Add a new task to the knowledge graph with hierarchy support. If use_context=true (default), auto-links to current project/task. Use parent_id to create subtasks.",
        inputSchema={
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Short subject/title for the task",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of what needs to be done",
                },
                "status": {
                    "type": "string",
                    "description": "Initial status (default: pending)",
                    "enum": ["pending", "in_progress", "completed", "blocked"],
                    "default": "pending",
                },
                "blocked_by": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Task IDs that block this task",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to associate with",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Optional parent task ID (makes this a subtask)",
                },
                "use_context": {
                    "type": "boolean",
                    "description": "If true (default), auto-use current context when parent_id/project_id not set",
                    "default": True,
                },
            },
            "required": ["subject", "description"],
        },
    ),
    Tool(
        name="update_task",
        description="Update an existing task's status, description, or parent. Use this to mark tasks as in progress, completed, blocked, or to move tasks under a different parent.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The ID of the task to update",
                },
                "status": {
                    "type": "string",
                    "description": "New status",
                    "enum": ["pending", "in_progress", "completed", "blocked"],
                },
                "description": {
                    "type": "string",
                    "description": "New description",
                },
                "parent_id": {
                    "type": "string",
                    "description": "New parent task or project ID to move this task under",
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="delete_task",
        description="Delete a task from the knowledge graph. Use with caution - this permanently removes the task. Can optionally delete all subtasks as well.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The ID of the task to delete",
                },
                "delete_subtasks": {
                    "type": "boolean",
                    "description": "If true, also delete all subtasks recursively (default: false)",
                    "default": False,
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="add_discovery",
        description="Record a learning or insight. When use_context=true (default), links to focus via 'led_to' edge (something led to this discovery) and becomes new focus.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "What was learned or discovered",
                },
                "context": {
                    "type": "string",
                    "description": "Where/how it was discovered",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to associate with",
                },
                "use_context": {
                    "type": "boolean",
                    "description": "If true (default), auto-link to focus and become new focus",
                    "default": True,
                },
                "parent_id": {
                    "type": "string",
                    "description": "Explicit parent node ID (overrides current focus)",
                },
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="get_project_context",
        description="Get comprehensive context for the current project including recent decisions, active tasks, and key discoveries. Use this at the start of a session to understand project state.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project ID (auto-detects from cwd if not provided)",
                },
            },
        },
    ),
    Tool(
        name="traverse_related",
        description="Explore relationships from a node in the knowledge graph. Use this to understand how entities are connected.",
        inputSchema={
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "The starting node ID",
                },
                "depth": {
                    "type": "integer",
                    "description": "How many hops to traverse (default: 1)",
                    "default": 1,
                },
                "edge_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by edge types: contains, references, blocks, spawned",
                },
            },
            "required": ["node_id"],
        },
    ),
    Tool(
        name="initialize_session",
        description="Initialize a manager session by gathering comprehensive project context. Call this at the START of a session when entering manager mode. Returns recent decisions, active tasks, discoveries, and suggested focus areas.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to scope the session",
                },
            },
        },
    ),
    # Context management tools
    Tool(
        name="get_context",
        description="Get the current working context (active project and task). New tasks created will automatically be linked to this context when use_context=true.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="set_context",
        description="Set the current working context. When a project is set, new tasks will be created under that project. When a task is set, new subtasks will be created under that task.",
        inputSchema={
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Project name or ID to set as active (or null to clear)",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID to set as active (or null to clear)",
                },
                "inferred_from": {
                    "type": "string",
                    "description": "How the context was determined: explicit, conversation, or cwd",
                    "enum": ["explicit", "conversation", "cwd"],
                    "default": "explicit",
                },
            },
        },
    ),
    Tool(
        name="create_project",
        description="Create a new project node. Projects are the top-level containers for tasks, decisions, and discoveries.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The project name (must be unique)",
                },
                "description": {
                    "type": "string",
                    "description": "Optional project description",
                    "default": "",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="list_projects",
        description="List all projects with summary stats including task counts.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="get_task_tree",
        description="Get hierarchical task tree under a project or task. Shows parent-child relationships in a tree structure.",
        inputSchema={
            "type": "object",
            "properties": {
                "root_id": {
                    "type": "string",
                    "description": "Project or task ID to start from",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth to traverse (default: 3)",
                    "default": 3,
                },
            },
            "required": ["root_id"],
        },
    ),
    # Knowledge-centric reasoning tools with context-aware parent linking
    Tool(
        name="add_thought",
        description="Record a reasoning step, observation, or chain of thought. When use_context=true (default), automatically links to current focus node and becomes the new focus, creating traversable reasoning trees.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The thought, observation, or reasoning step",
                },
                "context": {
                    "type": "string",
                    "description": "What prompted this thought",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization (e.g., 'reasoning', 'option-analysis', 'investigation')",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to associate with",
                },
                "use_context": {
                    "type": "boolean",
                    "description": "If true (default), auto-link to current focus and become new focus",
                    "default": True,
                },
                "parent_id": {
                    "type": "string",
                    "description": "Explicit parent node ID (overrides current focus)",
                },
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="add_constraint",
        description="Record a user preference or requirement that shapes decisions. When use_context=true (default), links to focus, becomes new focus, and collects for auto-linking when decision is made.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The constraint (e.g., 'User prefers desktop app', 'Must use Python 3.10+')",
                },
                "source": {
                    "type": "string",
                    "description": "Where this came from: user, requirement, technical, budget",
                    "default": "user",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level: low, medium, high, must-have",
                    "enum": ["low", "medium", "high", "must-have"],
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to associate with",
                },
                "use_context": {
                    "type": "boolean",
                    "description": "If true (default), auto-link to focus and collect for decision linking",
                    "default": True,
                },
                "parent_id": {
                    "type": "string",
                    "description": "Explicit parent node ID (overrides current focus)",
                },
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="add_problem",
        description="Record a problem or issue encountered. When use_context=true (default), links to focus, becomes new focus, and tracks as active_problem_id (auto-linked when add_fix is called).",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Description of the problem",
                },
                "context": {
                    "type": "string",
                    "description": "Where/when the problem was encountered",
                },
                "severity": {
                    "type": "string",
                    "description": "Severity level",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization (e.g., 'bug', 'blocker', 'config')",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to associate with",
                },
                "use_context": {
                    "type": "boolean",
                    "description": "If true (default), auto-link to focus and track as active problem",
                    "default": True,
                },
                "parent_id": {
                    "type": "string",
                    "description": "Explicit parent node ID (overrides current focus)",
                },
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="add_fix",
        description="Record a fix or solution to a problem. When use_context=true (default), auto-links to active_problem_id if no explicit problem_id, links to focus, and clears active problem.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Description of the fix/solution",
                },
                "problem_id": {
                    "type": "string",
                    "description": "ID of the problem this fixes. If not provided and use_context=true, uses active_problem_id",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about the fix",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags (e.g., 'workaround', 'permanent-fix', 'config-change')",
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project ID to associate with",
                },
                "use_context": {
                    "type": "boolean",
                    "description": "If true (default), auto-link to active problem and focus",
                    "default": True,
                },
                "parent_id": {
                    "type": "string",
                    "description": "Explicit parent node ID (overrides current focus)",
                },
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="link_nodes",
        description="Create an edge between two existing nodes. Use this to build reasoning chains: thought->decision, discovery->supports->decision, constraint->constrained_by->decision, problem->fixed_by->fix.",
        inputSchema={
            "type": "object",
            "properties": {
                "source_id": {
                    "type": "string",
                    "description": "UUID of the source node",
                },
                "target_id": {
                    "type": "string",
                    "description": "UUID of the target node",
                },
                "edge_type": {
                    "type": "string",
                    "description": "Type of relationship",
                    "enum": [
                        "led_to", "supports", "contradicts", "refined_by",
                        "constrained_by", "fixed_by", "contains", "references",
                        "related_to", "spawned", "blocked_by"
                    ],
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional additional properties for the edge",
                },
            },
            "required": ["source_id", "target_id", "edge_type"],
        },
    ),
    # Focus management tools for context-aware reasoning
    Tool(
        name="set_focus",
        description="Set focus to a specific node for automatic parent-based linking. Subsequent reasoning nodes will link to this as their parent, creating traversable reasoning trees.",
        inputSchema={
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "UUID of the node to focus on (task, problem, thought, etc.)",
                },
            },
            "required": ["node_id"],
        },
    ),
    Tool(
        name="clear_focus",
        description="Clear the current focus to stop automatic parent-based linking. New reasoning nodes will not auto-link.",
        inputSchema={
            "type": "object",
            "properties": {
                "keep_problem": {
                    "type": "boolean",
                    "description": "If true, keep active_problem_id for fix linking",
                    "default": False,
                },
            },
        },
    ),
    Tool(
        name="get_reasoning_context",
        description="Get the current reasoning context including focus node, active problem, and collected constraints. Useful for debugging or understanding current linking state.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return the list of available tools."""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool call: {name} with args: {arguments}")

    client = get_client()
    result: dict[str, Any]

    try:
        if name == "search_knowledge":
            result = await search_knowledge(
                client=client,
                query=arguments["query"],
                limit=arguments.get("limit", 10),
                min_score=arguments.get("min_score", 0.0),
            )

        elif name == "get_decisions":
            result = await get_decisions(
                client=client,
                project_id=arguments.get("project_id"),
                days=arguments.get("days", 90),
                limit=arguments.get("limit", 20),
            )

        elif name == "get_tasks":
            result = await get_tasks(
                client=client,
                status=arguments.get("status"),
                project_id=arguments.get("project_id"),
                parent_id=arguments.get("parent_id"),
                top_level_only=arguments.get("top_level_only", False),
                days=arguments.get("days", 30),
                limit=arguments.get("limit", 20),
            )

        elif name == "get_recent_activity":
            result = await get_recent_activity(
                client=client,
                hours=arguments.get("hours", 24),
                types=arguments.get("types"),
                limit=arguments.get("limit", 50),
            )

        elif name == "record_decision":
            result = await record_decision(
                client=client,
                title=arguments["title"],
                rationale=arguments["rationale"],
                alternatives=arguments.get("alternatives"),
                context=arguments.get("context"),
                project_id=arguments.get("project_id"),
                use_context=arguments.get("use_context", True),
                parent_id=arguments.get("parent_id"),
            )

        elif name == "add_task":
            result = await add_task(
                client=client,
                subject=arguments["subject"],
                description=arguments["description"],
                status=arguments.get("status", "pending"),
                blocked_by=arguments.get("blocked_by"),
                project_id=arguments.get("project_id"),
                parent_id=arguments.get("parent_id"),
                use_context=arguments.get("use_context", True),
            )

        elif name == "update_task":
            result = await update_task(
                client=client,
                task_id=arguments["task_id"],
                status=arguments.get("status"),
                description=arguments.get("description"),
                parent_id=arguments.get("parent_id"),
            )

        elif name == "delete_task":
            result = await delete_task(
                client=client,
                task_id=arguments["task_id"],
                delete_subtasks=arguments.get("delete_subtasks", False),
            )

        elif name == "add_discovery":
            result = await add_discovery(
                client=client,
                content=arguments["content"],
                context=arguments.get("context"),
                tags=arguments.get("tags"),
                project_id=arguments.get("project_id"),
                use_context=arguments.get("use_context", True),
                parent_id=arguments.get("parent_id"),
            )

        elif name == "get_project_context":
            result = await get_project_context(
                client=client,
                project_id=arguments.get("project_id"),
            )

        elif name == "traverse_related":
            result = await traverse_related(
                client=client,
                node_id=arguments["node_id"],
                depth=arguments.get("depth", 1),
                edge_types=arguments.get("edge_types"),
            )

        elif name == "initialize_session":
            result = await initialize_session(
                client=client,
                project_id=arguments.get("project_id"),
            )

        # Context management tools
        elif name == "get_context":
            result = await get_context(
                client=client,
            )

        elif name == "set_context":
            result = await set_context(
                client=client,
                project=arguments.get("project"),
                task_id=arguments.get("task_id"),
                inferred_from=arguments.get("inferred_from", "explicit"),
            )

        elif name == "create_project":
            result = await create_project(
                client=client,
                name=arguments["name"],
                description=arguments.get("description", ""),
            )

        elif name == "list_projects":
            result = await list_projects(
                client=client,
            )

        elif name == "get_task_tree":
            result = await get_task_tree(
                client=client,
                root_id=arguments["root_id"],
                max_depth=arguments.get("max_depth", 3),
            )

        # Knowledge-centric reasoning tools with context-aware parent linking
        elif name == "add_thought":
            result = await add_thought(
                client=client,
                content=arguments["content"],
                context=arguments.get("context"),
                tags=arguments.get("tags"),
                project_id=arguments.get("project_id"),
                use_context=arguments.get("use_context", True),
                parent_id=arguments.get("parent_id"),
            )

        elif name == "add_constraint":
            result = await add_constraint(
                client=client,
                content=arguments["content"],
                source=arguments.get("source"),
                priority=arguments.get("priority"),
                tags=arguments.get("tags"),
                project_id=arguments.get("project_id"),
                use_context=arguments.get("use_context", True),
                parent_id=arguments.get("parent_id"),
            )

        elif name == "add_problem":
            result = await add_problem(
                client=client,
                content=arguments["content"],
                context=arguments.get("context"),
                severity=arguments.get("severity"),
                tags=arguments.get("tags"),
                project_id=arguments.get("project_id"),
                use_context=arguments.get("use_context", True),
                parent_id=arguments.get("parent_id"),
            )

        elif name == "add_fix":
            result = await add_fix(
                client=client,
                content=arguments["content"],
                problem_id=arguments.get("problem_id"),
                context=arguments.get("context"),
                tags=arguments.get("tags"),
                project_id=arguments.get("project_id"),
                use_context=arguments.get("use_context", True),
                parent_id=arguments.get("parent_id"),
            )

        elif name == "link_nodes":
            result = await link_nodes(
                client=client,
                source_id=arguments["source_id"],
                target_id=arguments["target_id"],
                edge_type=arguments["edge_type"],
                metadata=arguments.get("metadata"),
            )

        # Focus management tools for context-aware reasoning
        elif name == "set_focus":
            result = await set_focus(
                client=client,
                node_id=arguments["node_id"],
            )

        elif name == "clear_focus":
            result = await clear_focus(
                client=client,
                keep_problem=arguments.get("keep_problem", False),
            )

        elif name == "get_reasoning_context":
            result = await get_reasoning_context(
                client=client,
            )

        else:
            result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        logger.exception(f"Error calling tool {name}")
        result = {"error": str(e)}

    # Convert result to JSON string for response
    import json
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def main():
    """Run the MCP server."""
    logger.info("Starting Knowledge Graph MCP Server")

    # Initialize client on startup
    get_client()

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
