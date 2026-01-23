"""
Knowledge Graph Dashboard

A Streamlit-based monitoring interface for the knowledge graph.
Displays projects, tasks, context, and recent activity.

Usage:
    streamlit run apps/dashboard/app.py
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node

# Page config
st.set_page_config(
    page_title="Knowledge Graph Dashboard",
    page_icon="🧠",
    layout="wide",
)

# Initialize client
@st.cache_resource
def get_client():
    """Get cached GraphitiClient instance."""
    client = GraphitiClient()
    client.connect()
    return client


def get_context(client: GraphitiClient) -> dict:
    """Get current working context."""
    context_nodes = client.query_nodes(filters={"type": "context"}, limit=1)
    if not context_nodes:
        return {}
    return context_nodes[0].metadata or {}


def get_projects(client: GraphitiClient) -> list:
    """Get all projects with task counts."""
    projects = client.query_nodes(filters={"type": "project"}, limit=100)
    tasks = client.query_nodes(filters={"type": "task"}, limit=1000)

    result = []
    for p in projects:
        metadata = p.metadata or {}
        task_count = sum(
            1 for t in tasks
            if t.metadata and t.metadata.get("project_id") == p.uuid
        )
        result.append({
            "id": p.uuid,
            "name": metadata.get("name", "Unnamed"),
            "description": metadata.get("description", ""),
            "task_count": task_count,
            "created_at": p.created_at,
        })

    return sorted(result, key=lambda x: x["name"].lower())


def get_tasks(client: GraphitiClient, project_id: str = None, parent_id: str = None) -> list:
    """Get tasks with optional filtering."""
    tasks = client.query_nodes(filters={"type": "task"}, limit=500)

    result = []
    for t in tasks:
        metadata = t.metadata or {}

        # Filter by project
        if project_id and metadata.get("project_id") != project_id:
            continue

        # Filter by parent
        if parent_id is not None:
            if metadata.get("parent_id") != parent_id:
                continue

        result.append({
            "id": t.uuid,
            "subject": metadata.get("subject", t.content[:50]),
            "description": metadata.get("description", ""),
            "status": metadata.get("status", "pending"),
            "parent_id": metadata.get("parent_id"),
            "project_id": metadata.get("project_id"),
            "depth": metadata.get("depth", 0),
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        })

    return sorted(result, key=lambda x: x["created_at"], reverse=True)


def get_recent_activity(client: GraphitiClient, hours: int = 24) -> list:
    """Get recent activity across all node types."""
    now = datetime.utcnow()
    start = now - timedelta(hours=hours)

    nodes = client.query_nodes_by_time(start, now)

    result = []
    for n in nodes:
        metadata = n.metadata or {}
        result.append({
            "id": n.uuid,
            "type": n.type,
            "title": metadata.get("subject") or metadata.get("title") or metadata.get("name") or n.content[:50],
            "created_at": n.created_at,
        })

    return sorted(result, key=lambda x: x["created_at"], reverse=True)[:50]


def get_decisions(client: GraphitiClient, limit: int = 20) -> list:
    """Get recent decisions."""
    decisions = client.query_nodes(filters={"type": "decision"}, limit=limit)

    result = []
    for d in decisions:
        metadata = d.metadata or {}
        result.append({
            "id": d.uuid,
            "title": metadata.get("title", d.content[:50]),
            "rationale": metadata.get("rationale", ""),
            "alternatives": metadata.get("alternatives", []),
            "created_at": d.created_at,
        })

    return sorted(result, key=lambda x: x["created_at"], reverse=True)


def build_task_tree(client: GraphitiClient, root_id: str, max_depth: int = 3) -> dict:
    """Build hierarchical task tree."""
    def build_node(node_id: str, depth: int) -> dict:
        node = client.get_node(node_id)
        if not node:
            return None

        metadata = node.metadata or {}
        tree_node = {
            "id": node.uuid,
            "type": node.type,
            "subject": metadata.get("subject") or metadata.get("name") or node.content[:50],
            "status": metadata.get("status"),
            "depth": depth,
            "children": [],
        }

        if depth >= max_depth:
            return tree_node

        # Find children via CONTAINS edges
        edges = client.query_edges(filters={"source_id": node_id, "type": "contains"}, limit=100)
        for edge in edges:
            child = build_node(edge.target_id, depth + 1)
            if child:
                tree_node["children"].append(child)

        # Also check parent_id metadata
        tasks = client.query_nodes(filters={"type": "task"}, limit=500)
        for task in tasks:
            if task.metadata and task.metadata.get("parent_id") == node_id:
                if not any(c["id"] == task.uuid for c in tree_node["children"]):
                    child = build_node(task.uuid, depth + 1)
                    if child:
                        tree_node["children"].append(child)

        tree_node["children"].sort(key=lambda x: x.get("subject", "").lower())
        return tree_node

    return build_node(root_id, 0)


def render_task_tree(tree: dict, indent: int = 0):
    """Render task tree recursively."""
    if not tree:
        return

    # Status emoji
    status_emoji = {
        "pending": "⏳",
        "in_progress": "🔄",
        "completed": "✅",
        "blocked": "🚫",
    }.get(tree.get("status"), "📋")

    # Type indicator
    type_indicator = "📁" if tree["type"] == "project" else status_emoji

    prefix = "  " * indent
    st.markdown(f"{prefix}{type_indicator} **{tree['subject']}** `{tree['id'][:8]}...`")

    for child in tree.get("children", []):
        render_task_tree(child, indent + 1)


# Main app
def main():
    st.title("🧠 Knowledge Graph Dashboard")

    client = get_client()

    # Sidebar - Current Context
    with st.sidebar:
        st.header("📍 Current Context")
        context = get_context(client)

        if context:
            if context.get("active_project_name"):
                st.success(f"**Project:** {context['active_project_name']}")
            else:
                st.info("No active project")

            if context.get("active_task_subject"):
                st.success(f"**Task:** {context['active_task_subject']}")
            else:
                st.info("No active task")

            if context.get("inferred_from"):
                st.caption(f"Set via: {context['inferred_from']}")
        else:
            st.warning("No context set")

        st.divider()

        # Quick stats
        st.header("📊 Quick Stats")
        projects = get_projects(client)
        all_tasks = get_tasks(client)

        col1, col2 = st.columns(2)
        col1.metric("Projects", len(projects))
        col2.metric("Tasks", len(all_tasks))

        pending = len([t for t in all_tasks if t["status"] == "pending"])
        in_progress = len([t for t in all_tasks if t["status"] == "in_progress"])
        completed = len([t for t in all_tasks if t["status"] == "completed"])

        col1, col2, col3 = st.columns(3)
        col1.metric("⏳ Pending", pending)
        col2.metric("🔄 Active", in_progress)
        col3.metric("✅ Done", completed)

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Projects", "📋 Tasks", "🎯 Decisions", "📜 Activity"])

    # Tab 1: Projects
    with tab1:
        st.header("Projects")
        projects = get_projects(client)

        if not projects:
            st.info("No projects yet. Create one via Claude: `create_project(name='my-project')`")
        else:
            for project in projects:
                with st.expander(f"📁 {project['name']} ({project['task_count']} tasks)", expanded=False):
                    st.write(f"**Description:** {project['description'] or 'No description'}")
                    st.write(f"**ID:** `{project['id']}`")
                    st.write(f"**Created:** {project['created_at'].strftime('%Y-%m-%d %H:%M')}")

                    # Show task tree
                    if st.button(f"Show Task Tree", key=f"tree_{project['id']}"):
                        tree = build_task_tree(client, project["id"])
                        if tree:
                            st.subheader("Task Hierarchy")
                            render_task_tree(tree)

    # Tab 2: Tasks
    with tab2:
        st.header("Tasks")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox(
                "Status",
                ["All", "pending", "in_progress", "completed", "blocked"],
            )
        with col2:
            project_filter = st.selectbox(
                "Project",
                ["All"] + [p["name"] for p in projects],
            )
        with col3:
            top_level = st.checkbox("Top-level only", value=False)

        # Get filtered tasks
        project_id = None
        if project_filter != "All":
            project_id = next((p["id"] for p in projects if p["name"] == project_filter), None)

        tasks = get_tasks(client, project_id=project_id)

        if status_filter != "All":
            tasks = [t for t in tasks if t["status"] == status_filter]

        if top_level:
            tasks = [t for t in tasks if not t["parent_id"]]

        if not tasks:
            st.info("No tasks match the filters")
        else:
            for task in tasks:
                status_emoji = {
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "blocked": "🚫",
                }.get(task["status"], "📋")

                depth_indicator = "↳ " * task["depth"] if task["depth"] > 0 else ""

                with st.expander(f"{status_emoji} {depth_indicator}{task['subject']}", expanded=False):
                    st.write(f"**Status:** {task['status']}")
                    st.write(f"**Description:** {task['description'] or 'No description'}")
                    st.write(f"**ID:** `{task['id']}`")
                    if task["parent_id"]:
                        st.write(f"**Parent:** `{task['parent_id'][:8]}...`")
                    st.write(f"**Depth:** {task['depth']}")
                    st.write(f"**Updated:** {task['updated_at'].strftime('%Y-%m-%d %H:%M')}")

    # Tab 3: Decisions
    with tab3:
        st.header("Decisions")
        decisions = get_decisions(client)

        if not decisions:
            st.info("No decisions recorded yet")
        else:
            for decision in decisions:
                with st.expander(f"🎯 {decision['title']}", expanded=False):
                    st.write(f"**Rationale:** {decision['rationale']}")
                    if decision["alternatives"]:
                        st.write(f"**Alternatives considered:** {', '.join(decision['alternatives'])}")
                    st.write(f"**ID:** `{decision['id']}`")
                    st.write(f"**Made:** {decision['created_at'].strftime('%Y-%m-%d %H:%M')}")

    # Tab 4: Recent Activity
    with tab4:
        st.header("Recent Activity")

        hours = st.slider("Hours to show", 1, 168, 24)
        activity = get_recent_activity(client, hours=hours)

        if not activity:
            st.info(f"No activity in the last {hours} hours")
        else:
            for item in activity:
                type_emoji = {
                    "task": "📋",
                    "decision": "🎯",
                    "discovery": "💡",
                    "project": "📁",
                    "session": "💬",
                    "context": "📍",
                }.get(item["type"], "📄")

                time_str = item["created_at"].strftime("%Y-%m-%d %H:%M")
                st.markdown(f"{type_emoji} **{item['type']}**: {item['title']} — *{time_str}*")

    # Footer
    st.divider()
    st.caption("Knowledge Graph Dashboard | Refresh page to update data")


if __name__ == "__main__":
    main()
