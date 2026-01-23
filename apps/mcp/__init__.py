"""
MCP Server for Knowledge Graph Integration

Exposes the Graphiti knowledge graph to Claude Code via Model Context Protocol,
enabling Claude to act as a project manager with persistent memory.
"""

from .knowledge_server import main

__all__ = ["main"]
