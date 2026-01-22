"""
Project Detection Module

Detects and identifies projects from the current directory by looking for
project markers like .git directories, .aios configuration, or other
project-specific files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class ProjectInfo:
    """
    Information about a detected project.

    Attributes:
        name: The project name (usually the directory name)
        path: Absolute path to the project root
        project_id: Unique identifier for the project (derived from path or .aios config)
        has_git: Whether the project has a .git directory
        has_aios: Whether the project has an .aios configuration directory
    """

    name: str
    path: Path
    project_id: str
    has_git: bool = False
    has_aios: bool = False


def detect_project(start_path: Optional[str] = None) -> Optional[ProjectInfo]:
    """
    Detect a project from the given path by searching for project markers.

    Searches upward from the starting path looking for .git or .aios directories
    to identify the project root. Returns information about the detected project
    or None if no project is found.

    Args:
        start_path: Path to start searching from. Defaults to current directory.

    Returns:
        ProjectInfo if a project is detected, None otherwise.

    Examples:
        >>> info = detect_project("/path/to/my/project/src")
        >>> if info:
        ...     print(f"Found project: {info.name}")
    """
    path = Path(start_path) if start_path else Path.cwd()
    path = path.resolve()

    # Search upward for project markers
    project_root = _find_project_root(path)

    if project_root is None:
        return None

    return _create_project_info(project_root)


def detect_project_id(start_path: Optional[str] = None) -> Optional[str]:
    """
    Detect and return only the project ID from the current location.

    A convenience function that returns just the project identifier,
    useful for scoped queries.

    Args:
        start_path: Path to start searching from. Defaults to current directory.

    Returns:
        The project ID string if detected, None otherwise.

    Examples:
        >>> project_id = detect_project_id()
        >>> if project_id:
        ...     print(f"Project ID: {project_id}")
    """
    info = detect_project(start_path)
    return info.project_id if info else None


def _find_project_root(start_path: Path) -> Optional[Path]:
    """
    Search upward from start_path to find a project root.

    A project root is identified by the presence of either:
    - .git directory (Git repository)
    - .aios directory (AIOS configuration)

    Args:
        start_path: Path to start searching from.

    Returns:
        Path to project root if found, None otherwise.
    """
    current = start_path

    # Traverse up to the filesystem root
    while current != current.parent:
        # Check for project markers
        if _has_project_marker(current):
            return current
        current = current.parent

    # Check the root directory itself
    if _has_project_marker(current):
        return current

    return None


def _has_project_marker(path: Path) -> bool:
    """
    Check if a directory contains project markers.

    Args:
        path: Directory path to check.

    Returns:
        True if .git or .aios directory exists, False otherwise.
    """
    git_dir = path / ".git"
    aios_dir = path / ".aios"
    return git_dir.exists() or aios_dir.exists()


def _create_project_info(project_root: Path) -> ProjectInfo:
    """
    Create a ProjectInfo object from a project root path.

    Args:
        project_root: Path to the project root directory.

    Returns:
        ProjectInfo with details about the project.
    """
    name = project_root.name
    has_git = (project_root / ".git").exists()
    has_aios = (project_root / ".aios").exists()

    # Generate project ID from the path
    # Use the directory name by default, but could be enhanced to read from .aios config
    project_id = _generate_project_id(project_root, has_aios)

    return ProjectInfo(
        name=name,
        path=project_root,
        project_id=project_id,
        has_git=has_git,
        has_aios=has_aios,
    )


def _generate_project_id(project_root: Path, has_aios: bool) -> str:
    """
    Generate a unique project identifier.

    If .aios/project_id exists, use that. Otherwise, generate an ID
    from the directory name and a hash of the path for uniqueness.

    Args:
        project_root: Path to the project root.
        has_aios: Whether the project has .aios configuration.

    Returns:
        A unique project identifier string.
    """
    # Try to read project ID from .aios config first
    if has_aios:
        project_id_file = project_root / ".aios" / "project_id"
        if project_id_file.exists():
            try:
                project_id = project_id_file.read_text().strip()
                if project_id:
                    return project_id
            except (OSError, IOError):
                pass  # Fall through to generated ID

    # Generate ID from project name and path hash for uniqueness
    # Use a simple hash of the absolute path to ensure uniqueness
    path_hash = abs(hash(str(project_root))) % (10**8)
    return f"{project_root.name}-{path_hash:08d}"


def get_project_markers(path: Optional[str] = None) -> dict[str, bool]:
    """
    Get a dictionary of project markers and their presence.

    Useful for debugging and status displays.

    Args:
        path: Path to check. Defaults to current directory.

    Returns:
        Dictionary mapping marker names to their existence status.

    Examples:
        >>> markers = get_project_markers()
        >>> print(markers)
        {'git': True, 'aios': False}
    """
    check_path = Path(path) if path else Path.cwd()
    check_path = check_path.resolve()

    return {
        "git": (check_path / ".git").exists(),
        "aios": (check_path / ".aios").exists(),
    }
