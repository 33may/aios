#!/usr/bin/env python3
"""
UserPromptSubmit hook that injects a reminder to record knowledge.

This hook runs on every prompt submission and adds context reminding
the agent to capture reasoning, constraints, and problems to the knowledge graph.
"""

import sys


def main():
    # Output reminder to be injected into context
    reminder = """<knowledge-capture-reminder>
BEFORE responding, check if you need to record knowledge:

1. **Reasoning/Analysis?** → add_thought (capture your analysis, options considered, trade-offs)
2. **User stated preference?** → add_constraint (e.g., "I prefer X", "must use Y", "don't want Z")
3. **Hit a problem?** → add_problem (errors, blockers, unexpected behavior)
4. **Made a decision?** → record_decision + link_nodes (connect thoughts that led to it)
5. **Fixed something?** → add_fix (link to the problem it solves)
6. **Learned something?** → add_discovery (insights, undocumented behavior)

**SOURCE ATTRIBUTION:** When recording knowledge, use tags to indicate source:
- `source:user` - Ideas/preferences explicitly stated by user
- `source:agent` - Your own reasoning, analysis, discoveries
- `source:external` - Information from web search, docs, external sources

After creating nodes, use link_nodes to connect related items (thought --led_to--> decision, etc.)

This is NOT optional. Capture knowledge as you work.
</knowledge-capture-reminder>"""

    # Output the reminder - it will be added to context
    print(reminder)
    sys.exit(0)


if __name__ == "__main__":
    main()
