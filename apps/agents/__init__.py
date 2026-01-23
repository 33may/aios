"""
Background Agents for Knowledge Graph Self-Organization

This package contains autonomous agents that run on schedules to:
- Link related nodes in the knowledge graph
- Research and expand incomplete knowledge
- Maintain graph health and organization
- Review sessions and extract knowledge

Agents:
- LinkerAgent: Finds and creates relationships between nodes (runs nightly)
- ResearcherAgent: Expands knowledge with external research (runs nightly)
- SessionReviewer: Reviews Claude sessions and extracts knowledge (runs on session end)
"""

from .base import BaseAgent, AgentResult
from .scheduler import AgentScheduler
from .linker import LinkerAgent
from .researcher import ResearcherAgent
from .session_reviewer import SessionReviewer

__all__ = [
    "BaseAgent",
    "AgentResult",
    "AgentScheduler",
    "LinkerAgent",
    "ResearcherAgent",
    "SessionReviewer",
]
