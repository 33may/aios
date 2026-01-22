"""
Natural Language Query CLI

Command-line interface for querying the knowledge base with natural language.
Ask questions like 'Why did we choose ROS2?' or 'What tasks are blocked?'
and get relevant answers with source attribution.
"""

from .main import main

__all__ = [
    "main",
]
