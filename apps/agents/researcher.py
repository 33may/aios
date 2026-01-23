"""
Researcher Agent - Expands knowledge by researching incomplete nodes.

Runs nightly to:
1. Find nodes with incomplete context or missing information
2. Use Claude API to research and expand knowledge
3. Create Discovery nodes with findings
4. Link discoveries to source nodes
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.agents.base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Maximum nodes to research per run
DEFAULT_MAX_NODES = 20

# Minimum content length to consider "complete"
DEFAULT_MIN_CONTENT_LENGTH = 100

# How far back to look for nodes needing research
DEFAULT_LOOKBACK_DAYS = 30

# Optional: Try to import anthropic for Claude API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


class ResearcherAgent(BaseAgent):
    """
    Agent that researches and expands incomplete knowledge.

    The researcher agent runs nightly to:
    1. Find nodes with sparse content or missing context
    2. Use Claude API to generate research questions and findings
    3. Create Discovery nodes with expanded knowledge
    4. Link discoveries back to the source nodes

    Configuration:
        max_nodes: Maximum nodes to research per run
        min_content_length: Minimum content length to consider "complete"
        lookback_days: How far back to look for nodes
        anthropic_api_key: API key for Claude (or set ANTHROPIC_API_KEY env var)
    """

    def __init__(
        self,
        client: Optional[GraphitiClient] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name="researcher", client=client, config=config)

        self.max_nodes = self.get_config("max_nodes", DEFAULT_MAX_NODES)
        self.min_content_length = self.get_config("min_content_length", DEFAULT_MIN_CONTENT_LENGTH)
        self.lookback_days = self.get_config("lookback_days", DEFAULT_LOOKBACK_DAYS)

        # Set up Anthropic client
        self.api_key = self.get_config("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_client = None

        if ANTHROPIC_AVAILABLE and self.api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("Anthropic client initialized for research")
        else:
            logger.warning(
                "Anthropic client not available - researcher will create placeholder discoveries"
            )

    async def execute(self) -> AgentResult:
        """Execute the researcher agent."""
        logger.info(
            f"ResearcherAgent executing with max_nodes={self.max_nodes}, "
            f"lookback_days={self.lookback_days}"
        )

        nodes_processed = 0
        edges_created = 0
        discoveries_created = 0

        try:
            # Find nodes that need research
            nodes_to_research = await self._find_incomplete_nodes()
            logger.info(f"Found {len(nodes_to_research)} nodes needing research")

            # Process each node
            for node in nodes_to_research[: self.max_nodes]:
                nodes_processed += 1

                try:
                    # Research the node
                    discovery_content = await self._research_node(node)

                    if discovery_content:
                        # Create discovery node
                        discovery = await self._create_discovery(node, discovery_content)
                        if discovery:
                            discoveries_created += 1

                            # Link discovery to source node
                            if await self._link_discovery(node, discovery):
                                edges_created += 1

                except Exception as e:
                    self._log_error(f"Failed to research node {node.uuid}", e)

            return self._create_result(
                success=True,
                nodes_processed=nodes_processed,
                edges_created=edges_created,
                details={
                    "discoveries_created": discoveries_created,
                    "api_available": self.anthropic_client is not None,
                },
            )

        except Exception as e:
            self._log_error("ResearcherAgent execution failed", e)
            return self._create_result(
                success=False,
                nodes_processed=nodes_processed,
                edges_created=edges_created,
            )

    async def _find_incomplete_nodes(self) -> List[Node]:
        """Find nodes that would benefit from additional research."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=self.lookback_days)

        # Get recent nodes
        recent_nodes = self.client.query_nodes_by_time(
            start=start_time,
            end=end_time,
            node_type=None,
        )

        incomplete = []
        for node in recent_nodes:
            score = self._calculate_completeness_score(node)
            if score < 0.5:  # Less than 50% complete
                incomplete.append(node)

        # Sort by completeness score (most incomplete first)
        incomplete.sort(
            key=lambda n: self._calculate_completeness_score(n)
        )

        return incomplete

    def _calculate_completeness_score(self, node: Node) -> float:
        """
        Calculate how "complete" a node is.

        Factors:
        - Content length
        - Has embedding
        - Has metadata
        - Node type (decisions should have rationale, tasks should have description)

        Returns:
            Score from 0.0 (incomplete) to 1.0 (complete)
        """
        score = 0.0

        # Content length (up to 0.4)
        content_len = len(node.content)
        if content_len >= self.min_content_length * 2:
            score += 0.4
        elif content_len >= self.min_content_length:
            score += 0.2
        elif content_len >= self.min_content_length / 2:
            score += 0.1

        # Has embedding (0.2)
        if node.embedding:
            score += 0.2

        # Has metadata (0.2)
        if node.metadata and len(node.metadata) > 0:
            score += 0.1
            # Extra points for meaningful metadata
            meaningful_keys = {"rationale", "alternatives", "context", "description", "status"}
            if any(k in node.metadata for k in meaningful_keys):
                score += 0.1

        # Type-specific completeness (0.2)
        if node.type == "decision":
            metadata = node.metadata or {}
            if metadata.get("rationale"):
                score += 0.1
            if metadata.get("alternatives"):
                score += 0.1
        elif node.type == "task":
            metadata = node.metadata or {}
            if metadata.get("description") and len(metadata.get("description", "")) > 50:
                score += 0.2
        else:
            # Other types get full points if they have substantial content
            if content_len >= self.min_content_length:
                score += 0.2

        return min(score, 1.0)

    async def _research_node(self, node: Node) -> Optional[str]:
        """
        Research a node using Claude API.

        Args:
            node: The node to research

        Returns:
            Research findings as a string, or None if research failed
        """
        if not self.anthropic_client:
            # Return placeholder for nodes without API access
            return self._create_placeholder_research(node)

        # Build prompt based on node type
        prompt = self._build_research_prompt(node)

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Use Haiku for cost efficiency
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            return response.content[0].text

        except Exception as e:
            self._log_error(f"Claude API call failed for node {node.uuid}", e)
            return None

    def _build_research_prompt(self, node: Node) -> str:
        """Build a research prompt based on node type and content."""
        base_context = f"""
You are a research assistant helping to expand knowledge about a {node.type}.

Current content:
{node.content}

Metadata:
{node.metadata or "None"}
"""

        if node.type == "decision":
            return base_context + """
Please provide:
1. Potential alternatives that weren't considered
2. Common pitfalls or risks with this approach
3. Best practices related to this decision

Keep your response concise (2-3 sentences per point).
"""
        elif node.type == "task":
            return base_context + """
Please provide:
1. Key steps or considerations for completing this task
2. Potential blockers or dependencies to watch for
3. Success criteria or how to verify completion

Keep your response concise (2-3 sentences per point).
"""
        else:
            return base_context + """
Please provide:
1. Additional context that would be helpful
2. Related concepts or connections
3. Key questions to consider

Keep your response concise (2-3 sentences per point).
"""

    def _create_placeholder_research(self, node: Node) -> str:
        """Create placeholder research when API is not available."""
        return f"""
[Placeholder Research for {node.type}]

This node could benefit from additional research:
- Content length: {len(node.content)} characters
- Has embedding: {node.embedding is not None}
- Metadata keys: {list(node.metadata.keys()) if node.metadata else "None"}

To enable automatic research, set the ANTHROPIC_API_KEY environment variable.
"""

    async def _create_discovery(
        self,
        source_node: Node,
        content: str,
    ) -> Optional[Node]:
        """Create a discovery node with research findings."""
        try:
            discovery = Node(
                type="discovery",
                content=content,
                metadata={
                    "source_node_id": source_node.uuid,
                    "source_node_type": source_node.type,
                    "created_by": "researcher_agent",
                    "research_date": datetime.now(timezone.utc).isoformat(),
                },
            )

            self.client.add_node(discovery)
            logger.info(f"Created discovery {discovery.uuid} for node {source_node.uuid}")
            return discovery

        except Exception as e:
            self._log_error(f"Failed to create discovery for node {source_node.uuid}", e)
            return None

    async def _link_discovery(
        self,
        source_node: Node,
        discovery: Node,
    ) -> bool:
        """Create an edge linking the discovery to its source node."""
        try:
            edge = Edge(
                type="references",
                source_id=discovery.uuid,
                target_id=source_node.uuid,
                metadata={
                    "relationship": "researched_from",
                    "created_by": "researcher_agent",
                },
            )

            self.client.add_edge(edge)
            logger.info(f"Linked discovery {discovery.uuid} to node {source_node.uuid}")
            return True

        except Exception as e:
            self._log_error(
                f"Failed to link discovery {discovery.uuid} to node {source_node.uuid}",
                e,
            )
            return False
