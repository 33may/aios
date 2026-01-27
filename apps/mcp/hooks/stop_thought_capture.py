#!/usr/bin/env python3
"""
Stop hook that prompts agent to capture final thoughts before ending.

Fires when Claude finishes responding (natural stop, not interrupt).
"""

import sys


def main():
    reminder = """<final-thought-capture>
BEFORE STOPPING: Capture any unrecorded reasoning:

1. What was your main conclusion? → add_thought or record_decision
2. Any unresolved questions? → add_thought with tag "open-question"
3. What would you investigate next? → add_thought with tag "next-step"
4. Any contradictions or tensions found? → add_thought with tag "contradiction"

Link your thoughts: thought1 --led_to--> thought2 --led_to--> decision

Source tags: source:agent for your reasoning, source:user for user ideas
</final-thought-capture>"""

    print(reminder)
    sys.exit(0)


if __name__ == "__main__":
    main()
