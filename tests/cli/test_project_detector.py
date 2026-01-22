"""
Tests for Project Detection Module

Tests project root detection, project info creation, project ID generation,
and project markers functionality.
"""

import pytest
from pathlib import Path
from apps.cli.project_detector import (
    ProjectInfo,
    detect_project,
    detect_project_id,
    get_project_markers,
    _find_project_root,
    _has_project_marker,
    _create_project_info,
    _generate_project_id,
)


# ProjectInfo Dataclass Tests


class TestProjectInfo:
    """Tests for ProjectInfo dataclass."""

    def test_project_info_creation(self):
        """Test that ProjectInfo can be created with required fields."""
        info = ProjectInfo(
            name="my-project",
            path=Path("/tmp/my-project"),
            project_id="my-project-12345678",
        )

        assert info.name == "my-project"
        assert info.path == Path("/tmp/my-project")
        assert info.project_id == "my-project-12345678"
        assert info.has_git is False
        assert info.has_aios is False

    def test_project_info_with_markers(self):
        """Test ProjectInfo with has_git and has_aios flags."""
        info = ProjectInfo(
            name="my-project",
            path=Path("/tmp/my-project"),
            project_id="my-project-12345678",
            has_git=True,
            has_aios=True,
        )

        assert info.has_git is True
        assert info.has_aios is True


# Project Detection Tests


class TestDetectProject:
    """Tests for detect_project function."""

    def test_detect_project_with_git(self, tmp_path: Path):
        """Test detecting project with .git directory."""
        # Create .git directory
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = detect_project(str(tmp_path))

        assert result is not None
        assert isinstance(result, ProjectInfo)
        assert result.path == tmp_path
        assert result.has_git is True
        assert result.has_aios is False

    def test_detect_project_with_aios(self, tmp_path: Path):
        """Test detecting project with .aios directory."""
        # Create .aios directory
        aios_dir = tmp_path / ".aios"
        aios_dir.mkdir()

        result = detect_project(str(tmp_path))

        assert result is not None
        assert result.path == tmp_path
        assert result.has_git is False
        assert result.has_aios is True

    def test_detect_project_with_both_markers(self, tmp_path: Path):
        """Test detecting project with both .git and .aios directories."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".aios").mkdir()

        result = detect_project(str(tmp_path))

        assert result is not None
        assert result.has_git is True
        assert result.has_aios is True

    def test_detect_project_from_subdirectory(self, tmp_path: Path):
        """Test detecting project when starting from a subdirectory."""
        # Create project root with .git
        (tmp_path / ".git").mkdir()

        # Create nested subdirectory
        nested_dir = tmp_path / "src" / "components"
        nested_dir.mkdir(parents=True)

        result = detect_project(str(nested_dir))

        assert result is not None
        assert result.path == tmp_path

    def test_detect_project_no_markers(self, tmp_path: Path):
        """Test detecting project returns None when no markers exist."""
        # Create an empty directory structure
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = detect_project(str(empty_dir))

        assert result is None

    def test_detect_project_name_from_directory(self, tmp_path: Path):
        """Test that project name is derived from directory name."""
        project_dir = tmp_path / "my-awesome-project"
        project_dir.mkdir()
        (project_dir / ".git").mkdir()

        result = detect_project(str(project_dir))

        assert result is not None
        assert result.name == "my-awesome-project"

    def test_detect_project_resolves_path(self, tmp_path: Path):
        """Test that project path is resolved to absolute path."""
        (tmp_path / ".git").mkdir()

        result = detect_project(str(tmp_path))

        assert result is not None
        assert result.path.is_absolute()


# Project ID Detection Tests


class TestDetectProjectId:
    """Tests for detect_project_id function."""

    def test_detect_project_id_returns_string(self, tmp_path: Path):
        """Test that detect_project_id returns a string."""
        (tmp_path / ".git").mkdir()

        result = detect_project_id(str(tmp_path))

        assert result is not None
        assert isinstance(result, str)

    def test_detect_project_id_returns_none_when_no_project(self, tmp_path: Path):
        """Test that detect_project_id returns None when no project found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = detect_project_id(str(empty_dir))

        assert result is None

    def test_detect_project_id_matches_project_info(self, tmp_path: Path):
        """Test that detect_project_id matches ProjectInfo.project_id."""
        (tmp_path / ".git").mkdir()

        project_id = detect_project_id(str(tmp_path))
        project_info = detect_project(str(tmp_path))

        assert project_id is not None
        assert project_info is not None
        assert project_id == project_info.project_id


# Find Project Root Tests


class TestFindProjectRoot:
    """Tests for _find_project_root internal function."""

    def test_find_project_root_direct(self, tmp_path: Path):
        """Test finding project root when starting at root."""
        (tmp_path / ".git").mkdir()

        result = _find_project_root(tmp_path)

        assert result == tmp_path

    def test_find_project_root_from_nested(self, tmp_path: Path):
        """Test finding project root from nested directory."""
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)

        result = _find_project_root(nested)

        assert result == tmp_path

    def test_find_project_root_not_found(self, tmp_path: Path):
        """Test that returns None when no project root found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = _find_project_root(empty_dir)

        assert result is None

    def test_find_project_root_stops_at_first_marker(self, tmp_path: Path):
        """Test that traversal stops at first project marker."""
        # Create nested project structure
        outer_project = tmp_path / "outer"
        outer_project.mkdir()
        (outer_project / ".git").mkdir()

        inner_project = outer_project / "inner"
        inner_project.mkdir()
        (inner_project / ".git").mkdir()

        # Starting from inner project should find inner, not outer
        result = _find_project_root(inner_project)

        assert result == inner_project


# Has Project Marker Tests


class TestHasProjectMarker:
    """Tests for _has_project_marker internal function."""

    def test_has_project_marker_with_git(self, tmp_path: Path):
        """Test that .git directory is detected as marker."""
        (tmp_path / ".git").mkdir()

        result = _has_project_marker(tmp_path)

        assert result is True

    def test_has_project_marker_with_aios(self, tmp_path: Path):
        """Test that .aios directory is detected as marker."""
        (tmp_path / ".aios").mkdir()

        result = _has_project_marker(tmp_path)

        assert result is True

    def test_has_project_marker_with_both(self, tmp_path: Path):
        """Test that both markers returns True."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".aios").mkdir()

        result = _has_project_marker(tmp_path)

        assert result is True

    def test_has_project_marker_empty_dir(self, tmp_path: Path):
        """Test that empty directory returns False."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = _has_project_marker(empty_dir)

        assert result is False

    def test_has_project_marker_other_files(self, tmp_path: Path):
        """Test that other files/directories don't trigger detection."""
        (tmp_path / "src").mkdir()
        (tmp_path / "README.md").write_text("# Project")

        result = _has_project_marker(tmp_path)

        assert result is False


# Create Project Info Tests


class TestCreateProjectInfo:
    """Tests for _create_project_info internal function."""

    def test_create_project_info_with_git(self, tmp_path: Path):
        """Test creating ProjectInfo for git project."""
        (tmp_path / ".git").mkdir()

        result = _create_project_info(tmp_path)

        assert isinstance(result, ProjectInfo)
        assert result.path == tmp_path
        assert result.name == tmp_path.name
        assert result.has_git is True
        assert result.has_aios is False

    def test_create_project_info_with_aios(self, tmp_path: Path):
        """Test creating ProjectInfo for aios project."""
        (tmp_path / ".aios").mkdir()

        result = _create_project_info(tmp_path)

        assert result.has_git is False
        assert result.has_aios is True

    def test_create_project_info_generates_id(self, tmp_path: Path):
        """Test that ProjectInfo includes generated project ID."""
        (tmp_path / ".git").mkdir()

        result = _create_project_info(tmp_path)

        assert result.project_id is not None
        assert len(result.project_id) > 0


# Generate Project ID Tests


class TestGenerateProjectId:
    """Tests for _generate_project_id internal function."""

    def test_generate_project_id_without_aios(self, tmp_path: Path):
        """Test generating project ID without .aios config."""
        result = _generate_project_id(tmp_path, has_aios=False)

        assert isinstance(result, str)
        assert tmp_path.name in result

    def test_generate_project_id_from_aios_config(self, tmp_path: Path):
        """Test generating project ID from .aios/project_id file."""
        aios_dir = tmp_path / ".aios"
        aios_dir.mkdir()
        (aios_dir / "project_id").write_text("custom-project-id")

        result = _generate_project_id(tmp_path, has_aios=True)

        assert result == "custom-project-id"

    def test_generate_project_id_strips_whitespace(self, tmp_path: Path):
        """Test that project ID from file is stripped of whitespace."""
        aios_dir = tmp_path / ".aios"
        aios_dir.mkdir()
        (aios_dir / "project_id").write_text("  custom-id\n  ")

        result = _generate_project_id(tmp_path, has_aios=True)

        assert result == "custom-id"

    def test_generate_project_id_empty_file_fallback(self, tmp_path: Path):
        """Test that empty project_id file falls back to generated ID."""
        aios_dir = tmp_path / ".aios"
        aios_dir.mkdir()
        (aios_dir / "project_id").write_text("")

        result = _generate_project_id(tmp_path, has_aios=True)

        # Should fall back to generated ID
        assert tmp_path.name in result

    def test_generate_project_id_missing_file_fallback(self, tmp_path: Path):
        """Test fallback when .aios exists but project_id file doesn't."""
        aios_dir = tmp_path / ".aios"
        aios_dir.mkdir()

        result = _generate_project_id(tmp_path, has_aios=True)

        # Should fall back to generated ID
        assert tmp_path.name in result

    def test_generate_project_id_unique_for_different_paths(self, tmp_path: Path):
        """Test that different paths generate different IDs."""
        dir1 = tmp_path / "project1"
        dir2 = tmp_path / "project2"
        dir1.mkdir()
        dir2.mkdir()

        id1 = _generate_project_id(dir1, has_aios=False)
        id2 = _generate_project_id(dir2, has_aios=False)

        assert id1 != id2

    def test_generate_project_id_deterministic(self, tmp_path: Path):
        """Test that same path generates same ID consistently."""
        id1 = _generate_project_id(tmp_path, has_aios=False)
        id2 = _generate_project_id(tmp_path, has_aios=False)

        assert id1 == id2


# Get Project Markers Tests


class TestGetProjectMarkers:
    """Tests for get_project_markers utility function."""

    def test_get_project_markers_both_present(self, tmp_path: Path):
        """Test markers when both .git and .aios exist."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".aios").mkdir()

        result = get_project_markers(str(tmp_path))

        assert result == {"git": True, "aios": True}

    def test_get_project_markers_git_only(self, tmp_path: Path):
        """Test markers when only .git exists."""
        (tmp_path / ".git").mkdir()

        result = get_project_markers(str(tmp_path))

        assert result == {"git": True, "aios": False}

    def test_get_project_markers_aios_only(self, tmp_path: Path):
        """Test markers when only .aios exists."""
        (tmp_path / ".aios").mkdir()

        result = get_project_markers(str(tmp_path))

        assert result == {"git": False, "aios": True}

    def test_get_project_markers_none_present(self, tmp_path: Path):
        """Test markers when neither exists."""
        result = get_project_markers(str(tmp_path))

        assert result == {"git": False, "aios": False}

    def test_get_project_markers_returns_dict(self, tmp_path: Path):
        """Test that get_project_markers returns a dict."""
        result = get_project_markers(str(tmp_path))

        assert isinstance(result, dict)
        assert "git" in result
        assert "aios" in result


# Integration Tests


class TestProjectDetectionIntegration:
    """Integration tests for project detection workflow."""

    def test_full_workflow_with_aios_config(self, tmp_path: Path):
        """Test complete workflow with .aios configuration."""
        # Create project structure
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / ".git").mkdir()

        aios_dir = project_dir / ".aios"
        aios_dir.mkdir()
        (aios_dir / "project_id").write_text("my-custom-id")

        # Create nested directory
        nested = project_dir / "src" / "components"
        nested.mkdir(parents=True)

        # Detect from nested directory
        result = detect_project(str(nested))

        assert result is not None
        assert result.path == project_dir
        assert result.name == "my-project"
        assert result.project_id == "my-custom-id"
        assert result.has_git is True
        assert result.has_aios is True

    def test_nested_project_detection(self, tmp_path: Path):
        """Test detection with nested projects."""
        # Outer project
        outer = tmp_path / "outer"
        outer.mkdir()
        (outer / ".git").mkdir()

        # Inner project (monorepo pattern)
        inner = outer / "packages" / "inner"
        inner.mkdir(parents=True)
        (inner / ".git").mkdir()

        # Detect from inner project
        result = detect_project(str(inner))

        assert result is not None
        assert result.path == inner
        assert result.name == "inner"

    def test_markers_consistency_with_detection(self, tmp_path: Path):
        """Test that get_project_markers is consistent with detect_project."""
        (tmp_path / ".git").mkdir()

        markers = get_project_markers(str(tmp_path))
        project = detect_project(str(tmp_path))

        assert project is not None
        assert markers["git"] == project.has_git
        assert markers["aios"] == project.has_aios
