"""
Agent Scheduler for running background agents on cron-like schedules.

Uses APScheduler to run agents at specified times. Default schedule:
- LinkerAgent: 2:00 AM daily
- ResearcherAgent: 3:00 AM daily
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional, Type
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.agents.base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class AgentScheduler:
    """
    Scheduler for running background agents.

    Manages agent registration, scheduling, and execution.
    Supports both scheduled and manual agent runs.

    Example:
        scheduler = AgentScheduler()

        # Register agents
        scheduler.register_agent(LinkerAgent, cron="0 2 * * *")  # 2 AM
        scheduler.register_agent(ResearcherAgent, cron="0 3 * * *")  # 3 AM

        # Start the scheduler
        scheduler.start()
    """

    def __init__(self, client: Optional[GraphitiClient] = None):
        """
        Initialize the scheduler.

        Args:
            client: Optional shared GraphitiClient for all agents
        """
        self.client = client
        self._scheduler = AsyncIOScheduler()
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}
        self._results: List[AgentResult] = []

        # Set up job event listeners
        self._scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR,
        )

        logger.info("AgentScheduler initialized")

    def _ensure_client(self) -> GraphitiClient:
        """Ensure we have a connected client."""
        if self.client is None:
            self.client = GraphitiClient()

        if not self.client.is_connected():
            self.client.connect()

        return self.client

    def register_agent(
        self,
        agent_class: Type[BaseAgent],
        cron: Optional[str] = None,
        hour: Optional[int] = None,
        minute: int = 0,
        config: Optional[Dict] = None,
    ) -> None:
        """
        Register an agent to run on a schedule.

        Args:
            agent_class: The agent class to instantiate and run
            cron: Cron expression (e.g., "0 2 * * *" for 2 AM daily)
            hour: Hour to run (0-23), alternative to cron
            minute: Minute to run (0-59)
            config: Optional configuration for the agent
        """
        # Create agent instance
        client = self._ensure_client()
        agent = agent_class(client=client, config=config)

        self._agents[agent.name] = agent
        self._agent_classes[agent.name] = agent_class

        # Set up schedule
        if cron:
            trigger = CronTrigger.from_crontab(cron)
        elif hour is not None:
            trigger = CronTrigger(hour=hour, minute=minute)
        else:
            logger.warning(f"No schedule specified for {agent.name}, agent will only run manually")
            return

        # Add job to scheduler
        self._scheduler.add_job(
            self._run_agent,
            trigger=trigger,
            args=[agent.name],
            id=agent.name,
            name=f"Agent: {agent.name}",
            replace_existing=True,
        )

        logger.info(f"Registered agent {agent.name} with schedule: {trigger}")

    async def _run_agent(self, agent_name: str) -> AgentResult:
        """Run a specific agent by name."""
        agent = self._agents.get(agent_name)
        if not agent:
            logger.error(f"Agent not found: {agent_name}")
            return AgentResult(
                agent_name=agent_name,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                success=False,
                errors=[f"Agent not found: {agent_name}"],
            )

        result = await agent.run()
        self._results.append(result)

        # Keep only last 100 results
        if len(self._results) > 100:
            self._results = self._results[-100:]

        return result

    def _on_job_executed(self, event) -> None:
        """Handle job execution events."""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} completed successfully")

    async def run_agent_now(self, agent_name: str) -> AgentResult:
        """
        Run an agent immediately (outside of schedule).

        Args:
            agent_name: Name of the agent to run

        Returns:
            AgentResult from the execution
        """
        logger.info(f"Manual run requested for agent: {agent_name}")
        return await self._run_agent(agent_name)

    async def run_all_now(self) -> List[AgentResult]:
        """
        Run all registered agents immediately.

        Returns:
            List of AgentResults from all executions
        """
        logger.info("Manual run requested for all agents")
        results = []
        for agent_name in self._agents:
            result = await self._run_agent(agent_name)
            results.append(result)
        return results

    def start(self) -> None:
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("AgentScheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("AgentScheduler stopped")

    def get_results(self, limit: int = 10) -> List[AgentResult]:
        """Get recent execution results."""
        return self._results[-limit:]

    def get_next_run_times(self) -> Dict[str, Optional[datetime]]:
        """Get next scheduled run time for each agent."""
        result = {}
        for job in self._scheduler.get_jobs():
            result[job.id] = job.next_run_time
        return result

    def list_agents(self) -> List[str]:
        """Get list of registered agent names."""
        return list(self._agents.keys())


async def run_scheduler():
    """
    Run the agent scheduler as a standalone daemon.

    This function sets up signal handlers and runs the scheduler
    indefinitely until interrupted.
    """
    from apps.agents.linker import LinkerAgent
    from apps.agents.researcher import ResearcherAgent

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting Agent Scheduler daemon")

    # Create scheduler
    scheduler = AgentScheduler()

    # Register agents with default schedules
    scheduler.register_agent(LinkerAgent, hour=2, minute=0)  # 2:00 AM
    scheduler.register_agent(ResearcherAgent, hour=3, minute=0)  # 3:00 AM

    # Start scheduler
    scheduler.start()

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def shutdown_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        scheduler.stop()
        loop.stop()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    logger.info(f"Registered agents: {scheduler.list_agents()}")
    logger.info(f"Next run times: {scheduler.get_next_run_times()}")

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        scheduler.stop()
        if scheduler.client:
            scheduler.client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_scheduler())
