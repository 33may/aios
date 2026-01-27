#!/usr/bin/env python3
"""
PreToolUse hook that reminds agent to record thoughts before proceeding.

Fires before all tools.
"""

import sys


def main():
    reminder = """<thought-capture-checkpoint>
PAUSE: Before this tool call, have you recorded your current reasoning?

If you're:
- Analyzing options → add_thought with your analysis
- Forming a hypothesis → add_thought with your hypothesis
- Found something interesting → add_discovery
- Seeing a contradiction → add_thought with tag "contradiction"
- Building an argument → add_thought with tag "argument"

Tags to use: source:agent, reasoning, hypothesis, analysis, contradiction, argument, investigation

Don't skip this - your thought process IS the valuable output.
</thought-capture-checkpoint>"""

    print(reminder)
    sys.exit(0)


if __name__ == "__main__":
    main()
