"""
CLI Configuration

Defines configuration settings for the Natural Language Query CLI,
including backend connection, query behavior, and output preferences.
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class CLIConfig:
    """
    Configuration for the CLI application.

    This class encapsulates all settings required for the CLI to connect
    to the backend services and control query behavior.

    Attributes:
        backend_url: The URL of the Graphiti backend API
        backend_port: The port for the backend API
        timeout: Request timeout in seconds
        default_limit: Default number of results to return
        max_limit: Maximum allowed results per query
        project_id: Optional project ID for scoped queries
        auto_detect_project: Whether to auto-detect project from current directory
        output_format: Output format (text, json, or table)
        verbose: Enable verbose output
        color: Enable colored output
    """

    backend_url: str = field(default_factory=lambda: os.getenv("AIOS_BACKEND_URL", "http://localhost"))
    backend_port: int = field(default_factory=lambda: int(os.getenv("AIOS_BACKEND_PORT", "8000")))
    timeout: int = field(default_factory=lambda: int(os.getenv("AIOS_TIMEOUT", "30")))
    default_limit: int = field(default_factory=lambda: int(os.getenv("AIOS_DEFAULT_LIMIT", "10")))
    max_limit: int = field(default_factory=lambda: int(os.getenv("AIOS_MAX_LIMIT", "100")))
    project_id: Optional[str] = field(default_factory=lambda: os.getenv("AIOS_PROJECT_ID"))
    auto_detect_project: bool = field(default_factory=lambda: os.getenv("AIOS_AUTO_DETECT_PROJECT", "true").lower() == "true")
    output_format: str = field(default_factory=lambda: os.getenv("AIOS_OUTPUT_FORMAT", "text"))
    verbose: bool = field(default_factory=lambda: os.getenv("AIOS_VERBOSE", "false").lower() == "true")
    color: bool = field(default_factory=lambda: os.getenv("AIOS_COLOR", "true").lower() == "true")

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.backend_url:
            raise ValueError("Backend URL cannot be empty")
        if self.backend_port <= 0 or self.backend_port > 65535:
            raise ValueError(f"Invalid port number: {self.backend_port}")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.default_limit <= 0:
            raise ValueError("Default limit must be positive")
        if self.max_limit <= 0:
            raise ValueError("Max limit must be positive")
        if self.default_limit > self.max_limit:
            raise ValueError("Default limit cannot exceed max limit")
        if self.output_format not in ("text", "json", "table"):
            raise ValueError(f"Invalid output format: {self.output_format}. Must be 'text', 'json', or 'table'")

    @property
    def backend_endpoint(self) -> str:
        """
        Generate the full backend endpoint URL.

        Returns:
            A formatted URL for the backend API.
        """
        return f"{self.backend_url}:{self.backend_port}"

    @property
    def api_url(self) -> str:
        """
        Generate the API base URL.

        Returns:
            The full API base URL including /api/v1 path.
        """
        return f"{self.backend_endpoint}/api/v1"
