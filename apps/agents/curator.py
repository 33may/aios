#!/usr/bin/env python3
"""
Knowledge Graph Curator Agent

Uses Claude Code to intelligently reorganize the knowledge graph.
Runs as a subprocess so it has access to all configured MCP tools.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Curator prompt
CURATOR_PROMPT = """You are a Knowledge Curator. Your job is to reorganize the knowledge graph into a clean, navigable structure.

## Your Mission

### 1. Understand What Exists
- Use mcp__knowledge__initialize_session to see current state
- Use mcp__knowledge__get_recent_activity(hours={hours}) to see recent nodes
- Use mcp__knowledge__list_projects to see all projects
- Use mcp__knowledge__get_task_tree for each project to see structure

### 2. Find What's Wrong
Look for:
- **Orphan nodes**: Not linked to any parent
- **Misplaced nodes**: Linked to wrong parent
- **Missing links**: Related concepts not connected
- **Duplicates**: Same info captured multiple times

### 3. Fix the Structure
Use:
- mcp__knowledge__link_nodes to create relationships
- mcp__knowledge__move_node to change parents
- mcp__knowledge__delete_node for true duplicates (careful!)

### 4. Document What You Did
Provide a summary of changes made.

## Principles
- Think first, understand before changing
- Quality over speed
- Preserve intent - info is right, just misplaced
- Create connections - knowledge is valuable when connected

Start now. First call initialize_session, then get_recent_activity."""


def run_curator(hours: int = 24, verbose: bool = False) -> str:
    """Run the curator using Claude Code."""

    prompt = CURATOR_PROMPT.format(hours=hours)

    cmd = [
        "claude",
        "-p", prompt,
        "--dangerously-skip-permissions",
        "--output-format", "stream-json" if verbose else "text",
    ]

    print(f"Starting curator (reviewing last {hours} hours)...")
    print("=" * 60)

    if verbose:
        # Stream output in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        full_output = []
        try:
            assert process.stdout is not None
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # Handle different message types
                    if data.get("type") == "assistant":
                        content = data.get("message", {}).get("content", [])
                        for block in content:
                            if block.get("type") == "text":
                                text = block.get("text", "")
                                print(f"\n[THINKING]\n{text}")
                                full_output.append(text)
                            elif block.get("type") == "tool_use":
                                tool_name = block.get("name", "unknown")
                                tool_input = json.dumps(block.get("input", {}), indent=2)
                                if len(tool_input) > 300:
                                    tool_input = tool_input[:300] + "..."
                                print(f"\n[TOOL] {tool_name}")
                                print(f"  Input: {tool_input}")

                    elif data.get("type") == "tool_result":
                        result = data.get("content", "")
                        if len(result) > 500:
                            result = result[:500] + "..."
                        print(f"  Result: {result}")

                    elif data.get("type") == "result":
                        result_text = data.get("result", "")
                        full_output.append(result_text)

                except json.JSONDecodeError:
                    print(line)

        except KeyboardInterrupt:
            process.terminate()
            print("\nCurator interrupted.")
            return ""

        process.wait()
        return "\n".join(full_output)

    else:
        # Simple text output
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return ""
        return result.stdout


def save_summary(summary: str) -> Path:
    """Save summary to docs/summaries."""
    summaries_dir = PROJECT_ROOT / "docs" / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}.md"
    filepath = summaries_dir / filename

    if filepath.exists():
        time_str = datetime.now().strftime("%H%M%S")
        filename = f"{date_str}-{time_str}.md"
        filepath = summaries_dir / filename

    filepath.write_text(summary)
    return filepath


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Knowledge Graph Curator (uses Claude Code)")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    summary = run_curator(hours=args.hours, verbose=args.verbose)

    if summary:
        print("\n" + "=" * 60)
        print("CURATION COMPLETE")
        print("=" * 60)
        print(summary)

        # Save summary
        path = save_summary(summary)
        print(f"\nSummary saved to: {path}")


if __name__ == "__main__":
    main()
