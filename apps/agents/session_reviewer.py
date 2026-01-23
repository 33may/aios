#!/usr/bin/env python3
"""
Session Reviewer Agent

An AI agent that runs after a Claude Code session ends to:
1. Analyze the session transcript
2. Create decisions/tasks/discoveries that weren't captured
3. Link and organize nodes created during the session
4. Update the knowledge graph intelligently

This agent uses Claude to understand the session context and
make intelligent decisions about what to capture.

Input (via stdin): JSON with session_id, transcript_path, parsed, etc.
Output: Updates to knowledge graph
"""

import json
import sys
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "session_reviewer.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)

# Try to import anthropic
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None
    logger.warning("Anthropic SDK not available - using fallback mode")


# System prompt for the session reviewer
SYSTEM_PROMPT = """You are a Session Reviewer Agent. Your job is to analyze a Claude Code session transcript and extract important information to store in a knowledge graph.

You have access to these tools to update the knowledge graph:
- record_decision: Record architectural/design decisions made
- add_task: Add tasks that were identified or need follow-up
- add_discovery: Record learnings or insights discovered
- link_nodes: Create relationships between nodes

Analyze the session and:
1. Identify any DECISIONS made (technology choices, architectural decisions, approach selections)
2. Identify any TASKS created, completed, or mentioned as needing work
3. Identify any DISCOVERIES or learnings (insights, gotchas, important findings)
4. Note relationships between these items

For each item you identify:
- Only create it if it seems significant enough to remember
- Use clear, concise titles/subjects
- Include relevant context and rationale
- Link related items when appropriate

Respond with a JSON object containing:
{
  "decisions": [{"title": "...", "rationale": "...", "alternatives": ["..."], "context": "..."}],
  "tasks": [{"subject": "...", "description": "...", "status": "pending|completed"}],
  "discoveries": [{"content": "...", "context": "...", "tags": ["..."]}],
  "links": [{"from_type": "...", "from_index": 0, "to_type": "...", "to_index": 0, "relationship": "..."}],
  "session_summary": "Brief summary of what was accomplished in this session"
}

Only include items that are genuinely worth remembering. Quality over quantity."""


class SessionReviewer:
    """Agent that reviews sessions and updates the knowledge graph."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client: Optional[GraphitiClient] = None
        self.anthropic_client = None

        if ANTHROPIC_AVAILABLE and self.api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.api_key)

    def connect(self) -> None:
        """Connect to the knowledge graph."""
        self.client = GraphitiClient()
        self.client.connect()
        logger.info("Connected to knowledge graph")

    def disconnect(self) -> None:
        """Disconnect from the knowledge graph."""
        if self.client:
            self.client.disconnect()

    def review_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review a session and update the knowledge graph.

        Args:
            session_data: Session information including transcript

        Returns:
            Results of the review
        """
        session_id = session_data.get("session_id", "unknown")
        parsed = session_data.get("parsed", {})
        cwd = session_data.get("working_directory", "")

        logger.info(f"Reviewing session: {session_id}")

        # Build session content for analysis
        session_content = self._build_session_content(parsed)

        # Use Claude to analyze the session
        if self.anthropic_client:
            analysis = self._analyze_with_claude(session_content)
        else:
            analysis = self._fallback_analysis(parsed)

        if not analysis:
            logger.error("Failed to analyze session")
            return {"success": False, "error": "Analysis failed"}

        # Create nodes in the knowledge graph
        results = self._create_nodes(analysis, session_id, cwd)

        # Create session node
        session_node_id = self._create_session_node(
            session_id=session_id,
            summary=analysis.get("session_summary", "Session reviewed"),
            cwd=cwd,
            parsed=parsed,
            results=results,
        )

        # Link created nodes to session
        if session_node_id:
            self._link_to_session(session_node_id, results)

        return {
            "success": True,
            "session_id": session_id,
            "session_node_id": session_node_id,
            "decisions_created": len(results.get("decisions", [])),
            "tasks_created": len(results.get("tasks", [])),
            "discoveries_created": len(results.get("discoveries", [])),
        }

    def _build_session_content(self, parsed: Dict[str, Any]) -> str:
        """Build a readable session content for Claude to analyze."""
        parts = []

        user_messages = parsed.get("user_messages", [])
        assistant_messages = parsed.get("assistant_messages", [])
        tools_used = parsed.get("tools_used", [])
        files_modified = parsed.get("files_modified", [])

        parts.append("## Session Conversation\n")

        # Interleave messages (simplified)
        for i, user_msg in enumerate(user_messages[:20]):  # Limit to 20
            parts.append(f"**User:** {user_msg[:500]}\n")
            if i < len(assistant_messages):
                parts.append(f"**Assistant:** {assistant_messages[i][:500]}\n")

        if tools_used:
            parts.append(f"\n## Tools Used\n{', '.join(tools_used)}\n")

        if files_modified:
            parts.append(f"\n## Files Modified\n")
            for f in files_modified[:20]:
                parts.append(f"- {f}\n")

        return "\n".join(parts)

    def _analyze_with_claude(self, session_content: str) -> Optional[Dict[str, Any]]:
        """Use Claude to analyze the session content."""
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Use Haiku for cost efficiency
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Please analyze this session and extract important information:\n\n{session_content}",
                    }
                ],
            )

            # Parse the JSON response
            response_text = response.content[0].text

            # Try to find JSON in the response
            try:
                # Look for JSON block
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                elif "{" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_str = response_text[json_start:json_end]
                else:
                    logger.warning("No JSON found in response")
                    return None

                return json.loads(json_str)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return None

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return None

    def _fallback_analysis(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Simple fallback analysis when Claude is not available."""
        return {
            "decisions": [],
            "tasks": [],
            "discoveries": [],
            "links": [],
            "session_summary": f"Session with {len(parsed.get('user_messages', []))} messages, "
                              f"{len(parsed.get('tools_used', []))} tool uses, "
                              f"{len(parsed.get('files_modified', []))} files modified.",
        }

    def _create_nodes(
        self,
        analysis: Dict[str, Any],
        session_id: str,
        cwd: str,
    ) -> Dict[str, List[str]]:
        """Create nodes in the knowledge graph from analysis."""
        results = {
            "decisions": [],
            "tasks": [],
            "discoveries": [],
        }

        # Create decision nodes
        for decision in analysis.get("decisions", []):
            try:
                node = Node(
                    type="decision",
                    content=decision.get("title", "Untitled Decision"),
                    metadata={
                        "rationale": decision.get("rationale", ""),
                        "alternatives": decision.get("alternatives", []),
                        "context": decision.get("context", ""),
                        "session_id": session_id,
                        "created_by": "session_reviewer",
                        "working_directory": cwd,
                    },
                )
                node_id = self.client.add_node(node)
                results["decisions"].append(node_id)
                logger.info(f"Created decision: {node_id}")
            except Exception as e:
                logger.error(f"Failed to create decision: {e}")

        # Create task nodes
        for task in analysis.get("tasks", []):
            try:
                node = Node(
                    type="task",
                    content=task.get("subject", "Untitled Task"),
                    metadata={
                        "description": task.get("description", ""),
                        "status": task.get("status", "pending"),
                        "session_id": session_id,
                        "created_by": "session_reviewer",
                        "working_directory": cwd,
                    },
                )
                node_id = self.client.add_node(node)
                results["tasks"].append(node_id)
                logger.info(f"Created task: {node_id}")
            except Exception as e:
                logger.error(f"Failed to create task: {e}")

        # Create discovery nodes
        for discovery in analysis.get("discoveries", []):
            try:
                node = Node(
                    type="discovery",
                    content=discovery.get("content", "Untitled Discovery"),
                    metadata={
                        "context": discovery.get("context", ""),
                        "tags": discovery.get("tags", []),
                        "session_id": session_id,
                        "created_by": "session_reviewer",
                        "working_directory": cwd,
                    },
                )
                node_id = self.client.add_node(node)
                results["discoveries"].append(node_id)
                logger.info(f"Created discovery: {node_id}")
            except Exception as e:
                logger.error(f"Failed to create discovery: {e}")

        return results

    def _create_session_node(
        self,
        session_id: str,
        summary: str,
        cwd: str,
        parsed: Dict[str, Any],
        results: Dict[str, List[str]],
    ) -> Optional[str]:
        """Create a session node."""
        try:
            node = Node(
                type="session",
                content=summary,
                metadata={
                    "session_id": session_id,
                    "working_directory": cwd,
                    "prompt_count": len(parsed.get("user_messages", [])),
                    "tool_count": len(parsed.get("tools_used", [])),
                    "tools_used": parsed.get("tools_used", []),
                    "files_modified": parsed.get("files_modified", []),
                    "decisions_created": results.get("decisions", []),
                    "tasks_created": results.get("tasks", []),
                    "discoveries_created": results.get("discoveries", []),
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "created_by": "session_reviewer",
                },
            )
            node_id = self.client.add_node(node)
            logger.info(f"Created session node: {node_id}")
            return node_id
        except Exception as e:
            logger.error(f"Failed to create session node: {e}")
            return None

    def _link_to_session(
        self,
        session_node_id: str,
        results: Dict[str, List[str]],
    ) -> None:
        """Link created nodes to the session node."""
        all_node_ids = (
            results.get("decisions", []) +
            results.get("tasks", []) +
            results.get("discoveries", [])
        )

        for node_id in all_node_ids:
            try:
                edge = Edge(
                    type="spawned",
                    source_id=session_node_id,
                    target_id=node_id,
                    metadata={"created_by": "session_reviewer"},
                )
                self.client.add_edge(edge)
                logger.info(f"Linked {node_id} to session {session_node_id}")
            except Exception as e:
                logger.error(f"Failed to link node: {e}")


def main():
    """Main entry point."""
    # Ensure logs directory exists
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        logger.error("Invalid JSON input")
        sys.exit(1)

    logger.info(f"Session reviewer started for session: {input_data.get('session_id')}")

    # Create and run reviewer
    reviewer = SessionReviewer()

    try:
        reviewer.connect()
        results = reviewer.review_session(input_data)

        if results.get("success"):
            logger.info(f"Session review complete: {results}")
            print(json.dumps(results))
        else:
            logger.error(f"Session review failed: {results}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"Session reviewer error: {e}")
        sys.exit(1)

    finally:
        reviewer.disconnect()


if __name__ == "__main__":
    main()
