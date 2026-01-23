"""
Abstract base class for background agents.

All agents inherit from BaseAgent and implement the execute() method.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result of an agent execution."""

    agent_name: str
    started_at: datetime
    completed_at: datetime
    success: bool
    nodes_processed: int = 0
    edges_created: int = 0
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for logging/storage."""
        return {
            "agent_name": self.agent_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "nodes_processed": self.nodes_processed,
            "edges_created": self.edges_created,
            "errors": self.errors,
            "details": self.details,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all background agents.

    Agents are autonomous processes that run on schedules to maintain
    and enhance the knowledge graph. Each agent:
    - Has access to the GraphitiClient
    - Implements an execute() method
    - Returns an AgentResult with metrics

    Example:
        class MyAgent(BaseAgent):
            def __init__(self, client: GraphitiClient):
                super().__init__(name="my-agent", client=client)

            async def execute(self) -> AgentResult:
                # Agent logic here
                return self._create_result(success=True)
    """

    def __init__(
        self,
        name: str,
        client: Optional[GraphitiClient] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the agent.

        Args:
            name: Unique name for this agent
            client: GraphitiClient instance (creates new one if not provided)
            config: Optional configuration dictionary
        """
        self.name = name
        self.client = client
        self.config = config or {}
        self._start_time: Optional[datetime] = None
        self._errors: List[str] = []

        logger.info(f"Initialized agent: {name}")

    def _ensure_client(self) -> GraphitiClient:
        """Ensure we have a connected client."""
        if self.client is None:
            self.client = GraphitiClient()

        if not self.client.is_connected():
            self.client.connect()

        return self.client

    def _create_result(
        self,
        success: bool,
        nodes_processed: int = 0,
        edges_created: int = 0,
        details: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Create an AgentResult with timing info."""
        return AgentResult(
            agent_name=self.name,
            started_at=self._start_time or datetime.utcnow(),
            completed_at=datetime.utcnow(),
            success=success,
            nodes_processed=nodes_processed,
            edges_created=edges_created,
            errors=self._errors.copy(),
            details=details or {},
        )

    def _log_error(self, message: str, exc: Optional[Exception] = None) -> None:
        """Log an error and add to error list."""
        if exc:
            message = f"{message}: {exc}"
        self._errors.append(message)
        logger.error(f"[{self.name}] {message}")

    async def run(self) -> AgentResult:
        """
        Run the agent with proper setup and teardown.

        This method handles timing, error catching, and logging.
        Subclasses should implement execute() instead of this method.
        """
        self._start_time = datetime.utcnow()
        self._errors = []

        logger.info(f"[{self.name}] Starting execution")

        try:
            self._ensure_client()
            result = await self.execute()
            logger.info(
                f"[{self.name}] Completed in {result.duration_seconds:.2f}s - "
                f"processed {result.nodes_processed} nodes, "
                f"created {result.edges_created} edges"
            )
            return result

        except Exception as e:
            self._log_error("Execution failed", e)
            return self._create_result(success=False)

    @abstractmethod
    async def execute(self) -> AgentResult:
        """
        Execute the agent's main logic.

        Subclasses must implement this method with their specific functionality.

        Returns:
            AgentResult with execution metrics
        """
        pass

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
