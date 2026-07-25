"""Canonical, repository-contained POSIX path handling for persisted artifacts."""
from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


def repo_root(repo: Path | None) -> Path:
    return Path.cwd().resolve() if repo is None else Path(repo).resolve()


def is_absolute_path(path_value: str) -> bool:
    return Path(path_value).is_absolute() or PureWindowsPath(path_value).is_absolute()


def is_canonical_repo_relative_path(path_value: Any) -> bool:
    """Whether ``path_value`` is a canonical serialized repository path."""
    if not isinstance(path_value, str) or not path_value or "\\" in path_value:
        return False
    posix_path = PurePosixPath(path_value)
    windows_path = PureWindowsPath(path_value)
    return (
        path_value != "."
        and not is_absolute_path(path_value)
        and not windows_path.drive
        and ".." not in posix_path.parts
        and posix_path.as_posix() == path_value
    )


def _resolved_path_inside_repo(path: Path, repo: Path) -> Path | None:
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(repo)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved


def resolve_repo_relative_path(path_value: Any, repo: Path) -> Path | None:
    """Resolve a canonical serialized path only when it remains inside ``repo``."""
    if not is_canonical_repo_relative_path(path_value):
        return None
    root = repo_root(repo)
    return _resolved_path_inside_repo(root / Path(path_value), root)


def resolve_repo_input_path(path_value: Path | str, repo: Path) -> Path | None:
    """Resolve a caller path before accepting it as an in-repository artifact."""
    if isinstance(path_value, str):
        return resolve_repo_relative_path(path_value, repo)
    path = Path(path_value)
    root = repo_root(repo)
    if not path.is_absolute() and not is_canonical_repo_relative_path(str(path)):
        return None
    return _resolved_path_inside_repo(path if path.is_absolute() else root / path, root)


def resolve_repo_read_path(path_value: Path | str, repo: Path) -> Path | None:
    """Resolve a caller path inside ``repo`` before a filesystem read or scan.

    Unlike serialized artifact paths, public caller inputs may be absolute strings.
    The returned path is always resolved and repository-contained, so a symlink
    cannot redirect a later read or directory enumeration outside the repository.
    """
    root = repo_root(repo)
    if isinstance(path_value, str):
        if is_absolute_path(path_value):
            path = Path(path_value)
            return _resolved_path_inside_repo(path, root) if path.is_absolute() else None
        return resolve_repo_input_path(path_value, root)
    path = Path(path_value)
    if path.is_absolute():
        return _resolved_path_inside_repo(path, root)
    return resolve_repo_input_path(path, root)


def resolve_output_path(path_value: Path | str, repo: Path) -> Path:
    """Resolve a caller-selected output destination without artifact validation."""
    path = Path(path_value)
    return path if path.is_absolute() else repo_root(repo) / path


def canonical_repo_relative_path(path: Path, repo: Path) -> str | None:
    """Serialize a resolved in-repository path as canonical POSIX text."""
    root = repo_root(repo)
    resolved = resolve_repo_input_path(path, root)
    if resolved is None:
        return None
    value = resolved.relative_to(root).as_posix()
    return value if is_canonical_repo_relative_path(value) else None


def repo_relative_path(path: Path, repo: Path) -> str | None:
    """Return the canonical serialized path for an in-repository filesystem path."""
    root = repo_root(repo)
    resolved = resolve_repo_input_path(path, root)
    if resolved is None:
        return None
    return resolved.relative_to(root).as_posix()
