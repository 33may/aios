#!/usr/bin/env python3
"""
Session Capture Hook for Claude Code

This script runs on SessionEnd to capture the session transcript
and spawn a Session Reviewer Agent to process it.

The agent uses Claude to intelligently:
- Create decisions/tasks/discoveries that weren't captured
- Link and organize nodes created during the session
- Update the knowledge graph

Input (via stdin): JSON with session_id, transcript_path, reason, cwd
Output: Spawns session reviewer agent
"""

import json
import sys
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def parse_transcript_basic(transcript_path: str) -> Dict[str, Any]:
    """
    Basic parsing of transcript to extract raw content for the agent.

    The agent will do the intelligent analysis - we just extract the text.
    """
    if not os.path.exists(transcript_path):
        return {"error": f"Transcript not found: {transcript_path}"}

    user_messages = []
    assistant_messages = []
    tools_used = []
    files_modified = set()

    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get("type")

                if entry_type == "user":
                    message = entry.get("message", {})
                    content = message.get("content", "")
                    if isinstance(content, str) and len(content) > 5:
                        user_messages.append(content)
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if len(text) > 5:
                                    user_messages.append(text)

                elif entry_type == "assistant":
                    message = entry.get("message", {})
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text = block.get("text", "")
                                    if len(text) > 10:
                                        assistant_messages.append(text)
                                elif block.get("type") == "tool_use":
                                    tool_name = block.get("name", "unknown")
                                    tools_used.append(tool_name)
                                    tool_input = block.get("input", {})
                                    if isinstance(tool_input, dict):
                                        file_path = tool_input.get("file_path", tool_input.get("path"))
                                        if file_path and tool_name in ("Write", "Edit", "NotebookEdit"):
                                            files_modified.add(file_path)

    except Exception as e:
        return {"error": f"Failed to parse transcript: {e}"}

    return {
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "tools_used": list(set(tools_used)),
        "files_modified": list(files_modified),
    }


def spawn_session_reviewer(
    session_id: str,
    transcript_path: str,
    parsed: Dict[str, Any],
    cwd: str,
) -> bool:
    """
    Spawn the Session Reviewer Agent to process the transcript.

    The agent runs as a separate process using Claude to analyze
    the session and update the knowledge graph.
    """
    # Path to the session reviewer agent
    agent_script = PROJECT_ROOT / "apps" / "agents" / "session_reviewer.py"

    if not agent_script.exists():
        print(f"Session reviewer agent not found: {agent_script}", file=sys.stderr)
        return False

    # Prepare input for the agent
    agent_input = {
        "session_id": session_id,
        "transcript_path": transcript_path,
        "working_directory": cwd,
        "parsed": parsed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Spawn agent as background process
        process = subprocess.Popen(
            [sys.executable, str(agent_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
        )

        # Send input and don't wait (fire and forget)
        process.stdin.write(json.dumps(agent_input).encode())
        process.stdin.close()

        print(f"Session reviewer agent spawned (PID: {process.pid})")
        return True

    except Exception as e:
        print(f"Failed to spawn session reviewer: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for the hook."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("Invalid JSON input", file=sys.stderr)
        sys.exit(1)

    session_id = input_data.get("session_id", "unknown")
    transcript_path = input_data.get("transcript_path", "")
    reason = input_data.get("reason", "unknown")
    cwd = input_data.get("cwd", os.getcwd())

    if not transcript_path:
        print("No transcript path provided", file=sys.stderr)
        sys.exit(0)

    # Basic parsing
    parsed = parse_transcript_basic(transcript_path)

    # Skip empty sessions
    if not parsed.get("user_messages"):
        print("Empty session, skipping")
        sys.exit(0)

    # Spawn the session reviewer agent
    if spawn_session_reviewer(session_id, transcript_path, parsed, cwd):
        print(f"Session {session_id} queued for review")
    else:
        print("Failed to queue session for review", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
