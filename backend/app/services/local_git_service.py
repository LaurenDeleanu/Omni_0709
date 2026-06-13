import os
import subprocess
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _run_git(args: List[str], timeout: float = 30.0) -> str:
    process = subprocess.run(
        ["git"] + args,
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    if process.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {process.stderr.strip()}")
    return process.stdout.strip()


async def create_branch(branch_name: str, base_branch: str = "main") -> str:
    try:
        _run_git(["checkout", base_branch])
    except RuntimeError:
        pass
    _run_git(["checkout", "-b", branch_name])
    return branch_name


async def checkout_branch(branch_name: str) -> str:
    _run_git(["checkout", branch_name])
    return branch_name


async def get_current_branch() -> str:
    try:
        return _run_git(["branch", "--show-current"])
    except RuntimeError:
        return "main"


async def commit_changes(message: str, files: List[str]) -> str:
    if files:
        for f in files:
            _run_git(["add", f])
    else:
        _run_git(["add", "-A"])
    _run_git(["commit", "-m", message])
    return _run_git(["rev-parse", "HEAD"])


async def get_diff(file_path: Optional[str] = None) -> str:
    args = ["diff"]
    if file_path:
        args.append("--")
        args.append(file_path)
    try:
        return _run_git(args)
    except RuntimeError:
        return ""


async def get_diff_staged() -> str:
    try:
        return _run_git(["diff", "--staged"])
    except RuntimeError:
        return ""


async def get_unified_diff(base_branch: str, file_path: str) -> str:
    try:
        return _run_git(["diff", base_branch, "--", file_path])
    except RuntimeError:
        return ""


async def get_patch_from_commits(base_branch: str, branch_name: str) -> str:
    return _run_git(["format-patch", f"{base_branch}..{branch_name}", "--stdout"])


async def apply_patch(patch_path: str) -> str:
    return _run_git(["apply", patch_path])
