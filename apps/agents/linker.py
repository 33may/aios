"""
Linker Agent - Creates relationships between semantically similar nodes.

Runs nightly to:
1. Find nodes that were created/updated recently
2. Calculate embedding similarity between nodes
3. Create SIMILAR_TO or RELATES_TO edges for highly similar nodes
4. Identify decision->task relationships
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.agents.base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Similarity threshold for creating SIMILAR_TO edges
DEFAULT_SIMILARITY_THRESHOLD = 0.75

# Maximum nodes to process per run (to limit runtime)
DEFAULT_MAX_NODES = 500

# How far back to look for new nodes (in days)
DEFAULT_LOOKBACK_DAYS = 7


class LinkerAgent(BaseAgent):
    """
    Agent that finds and creates relationships between nodes.

    The linker agent runs nightly to:
    1. Process recent nodes (created in the last N days)
    2. Find semantically similar nodes using embedding comparison
    3. Create SIMILAR_TO edges between highly similar nodes
    4. Detect and create decision->task relationships

    Configuration:
        similarity_threshold: Minimum similarity score (0.0-1.0) for creating edges
        max_nodes: Maximum nodes to process per run
        lookback_days: How far back to look for new nodes
    """

    def __init__(
        self,
        client: Optional[GraphitiClient] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name="linker", client=client, config=config)

        self.similarity_threshold = self.get_config(
            "similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD
        )
        self.max_nodes = self.get_config("max_nodes", DEFAULT_MAX_NODES)
        self.lookback_days = self.get_config("lookback_days", DEFAULT_LOOKBACK_DAYS)

    async def execute(self) -> AgentResult:
        """Execute the linker agent."""
        logger.info(
            f"LinkerAgent executing with threshold={self.similarity_threshold}, "
            f"max_nodes={self.max_nodes}, lookback_days={self.lookback_days}"
        )

        nodes_processed = 0
        edges_created = 0
        similar_pairs: List[Tuple[str, str, float]] = []
        decision_task_links = 0

        try:
            # Get recent nodes
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=self.lookback_days)

            recent_nodes = self.client.query_nodes_by_time(
                start=start_time,
                end=end_time,
                node_type=None,
            )

            logger.info(f"Found {len(recent_nodes)} recent nodes to process")

            # Limit to max_nodes
            nodes_to_process = recent_nodes[: self.max_nodes]
            nodes_processed = len(nodes_to_process)

            # Get existing edges to avoid duplicates
            existing_edges = self._get_existing_edge_pairs()

            # Find similar pairs
            for i, node1 in enumerate(nodes_to_process):
                for node2 in nodes_to_process[i + 1:]:
                    # Skip if edge already exists
                    if (node1.uuid, node2.uuid) in existing_edges:
                        continue
                    if (node2.uuid, node1.uuid) in existing_edges:
                        continue

                    # Calculate similarity
                    similarity = self._calculate_similarity(node1, node2)
                    if similarity >= self.similarity_threshold:
                        similar_pairs.append((node1.uuid, node2.uuid, similarity))

            # Create edges for similar pairs
            for source_id, target_id, similarity in similar_pairs:
                try:
                    edge = Edge(
                        type="similar_to",
                        source_id=source_id,
                        target_id=target_id,
                        metadata={
                            "similarity_score": round(similarity, 4),
                            "created_by": "linker_agent",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    self.client.add_edge(edge)
                    edges_created += 1
                except Exception as e:
                    self._log_error(f"Failed to create edge {source_id}->{target_id}", e)

            # Find decision->task relationships
            decision_task_links = await self._link_decisions_to_tasks(
                nodes_to_process, existing_edges
            )
            edges_created += decision_task_links

            return self._create_result(
                success=True,
                nodes_processed=nodes_processed,
                edges_created=edges_created,
                details={
                    "similar_pairs_found": len(similar_pairs),
                    "decision_task_links": decision_task_links,
                    "similarity_threshold": self.similarity_threshold,
                    "lookback_days": self.lookback_days,
                },
            )

        except Exception as e:
            self._log_error("LinkerAgent execution failed", e)
            return self._create_result(
                success=False,
                nodes_processed=nodes_processed,
                edges_created=edges_created,
            )

    def _get_existing_edge_pairs(self) -> Set[Tuple[str, str]]:
        """Get set of existing edge pairs to avoid duplicates."""
        existing = set()
        try:
            edges = self.client.query_edges(limit=10000)
            for edge in edges:
                existing.add((edge.source_id, edge.target_id))
        except Exception as e:
            self._log_error("Failed to query existing edges", e)
        return existing

    def _calculate_similarity(self, node1: Node, node2: Node) -> float:
        """
        Calculate similarity between two nodes.

        Uses embedding cosine similarity if available, falls back to
        simple text similarity.
        """
        # If both have embeddings, use cosine similarity
        if node1.embedding and node2.embedding:
            return self._cosine_similarity(node1.embedding, node2.embedding)

        # Fall back to simple text-based similarity
        return self._text_similarity(node1.content, node2.content)

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """
        Simple text similarity using Jaccard coefficient on word sets.

        This is a fallback for nodes without embeddings.
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    async def _link_decisions_to_tasks(
        self,
        nodes: List[Node],
        existing_edges: Set[Tuple[str, str]],
    ) -> int:
        """
        Find and create decision->task relationships.

        Looks for tasks that were likely created as a result of decisions.
        Uses temporal proximity and content similarity.
        """
        edges_created = 0

        # Separate decisions and tasks
        decisions = [n for n in nodes if n.type == "decision"]
        tasks = [n for n in nodes if n.type == "task"]

        logger.info(f"Looking for decision->task links: {len(decisions)} decisions, {len(tasks)} tasks")

        for decision in decisions:
            for task in tasks:
                # Skip if edge already exists
                if (decision.uuid, task.uuid) in existing_edges:
                    continue

                # Check if task was created after decision
                if task.created_at < decision.created_at:
                    continue

                # Check if task was created within reasonable time window
                time_diff = task.created_at - decision.created_at
                if time_diff.days > 7:  # More than a week apart
                    continue

                # Check content similarity
                similarity = self._calculate_similarity(decision, task)
                if similarity < 0.3:  # Lower threshold for decision->task
                    continue

                # Create LED_TO edge
                try:
                    edge = Edge(
                        type="led_to",
                        source_id=decision.uuid,
                        target_id=task.uuid,
                        metadata={
                            "similarity_score": round(similarity, 4),
                            "time_diff_hours": round(time_diff.total_seconds() / 3600, 1),
                            "created_by": "linker_agent",
                        },
                    )
                    self.client.add_edge(edge)
                    edges_created += 1
                    existing_edges.add((decision.uuid, task.uuid))
                except Exception as e:
                    self._log_error(
                        f"Failed to create decision->task edge: {decision.uuid}->{task.uuid}",
                        e,
                    )

        return edges_created
