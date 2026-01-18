"""
File Tracker Module

Tracks file modifications and reads during agent execution.
Maintains separate registries for modified and read files per agent.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Set, Optional
from uuid import UUID
from pydantic import BaseModel

# Import from local modules
from .git_utils import GitUtils


# Pydantic models for type safety
class FileChange(BaseModel):
    path: str
    absolute_path: str
    status: str  # 'created' | 'modified' | 'deleted'
    lines_added: int
    lines_removed: int
    diff: Optional[str] = None
    summary: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None


class FileRead(BaseModel):
    path: str
    absolute_path: str
    line_count: int
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None


class AgentLogMetadata(BaseModel):
    """Metadata structure stored in agent_log.payload"""
    file_changes: Optional[List[FileChange]] = None
    read_files: Optional[List[FileRead]] = None
    total_files_modified: Optional[int] = None
    total_files_read: Optional[int] = None
    generated_at: Optional[str] = None


# Tool categories
FILE_MODIFYING_TOOLS = ["Write", "Edit", "MultiEdit", "Bash"]
FILE_READING_TOOLS = ["Read"]


class FileTracker:
    """Tracks file operations for a single agent."""

    def __init__(self, agent_id: UUID, agent_name: str, working_dir: str):
        """
        Initialize file tracker for an agent.

        Args:
            agent_id: UUID of the agent
            agent_name: Name of the agent
            working_dir: Working directory for file operations
        """
        self.agent_id = str(agent_id)
        self.agent_name = agent_name
        self.working_dir = working_dir

        # Use sets to track unique file paths
        self.modified_files: Set[str] = set()
        self.read_files: Set[str] = set()

        # Store detailed info for modified files
        self._file_details: Dict[str, Dict[str, Any]] = {}

    def track_modified_file(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """
        Record a file modification from a tool.

        Args:
            tool_name: Name of the tool (Write, Edit, etc.)
            tool_input: Tool input parameters
        """
        # Extract file_path from tool_input
        file_path = tool_input.get("file_path")

        if not file_path:
            return

        # Add to modified files set
        self.modified_files.add(file_path)

        # Store tool info for later summary generation
        if file_path not in self._file_details:
            self._file_details[file_path] = {
                "tool_name": tool_name,
                "tool_input": tool_input
            }

    def track_read_file(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """
        Record a file read from a tool.

        Args:
            tool_name: Name of the tool (Read, etc.)
            tool_input: Tool input parameters
        """
        # Extract file_path from tool_input
        file_path = tool_input.get("file_path")

        if not file_path:
            return

        # Add to read files set
        self.read_files.add(file_path)

    def get_file_changes_metadata(self) -> Optional[List[FileChange]]:
        """
        Generate detailed metadata for all modified files.

        Returns:
            List of FileChange objects with full details
        """
        if not self.modified_files:
            return None

        file_changes: List[FileChange] = []

        for file_path in self.modified_files:
            try:
                # Resolve to absolute path
                abs_path = GitUtils.resolve_absolute_path(file_path, self.working_dir)

                # Get file diff
                diff = GitUtils.get_file_diff(file_path, self.working_dir)
                lines_added, lines_removed = GitUtils.parse_diff_stats(diff) if diff else (0, 0)

                # Get file status
                status = GitUtils.get_file_status(file_path, self.working_dir)

                file_change = FileChange(
                    path=file_path,
                    absolute_path=abs_path,
                    status=status,
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                    diff=diff,
                    agent_id=self.agent_id,
                    agent_name=self.agent_name
                )
                file_changes.append(file_change)

            except Exception as e:
                # Log error but continue with other files
                print(f"Error processing file {file_path}: {e}")
                continue

        return file_changes if file_changes else None

    def get_read_files_metadata(self) -> Optional[List[FileRead]]:
        """
        Generate metadata for all read files.

        Returns:
            List of FileRead objects with file line counts
        """
        if not self.read_files:
            return None

        read_files_list: List[FileRead] = []

        for file_path in self.read_files:
            try:
                # Resolve to absolute path
                abs_path = GitUtils.resolve_absolute_path(file_path, self.working_dir)

                # Count lines
                line_count = GitUtils.count_file_lines(file_path, self.working_dir)

                file_read = FileRead(
                    path=file_path,
                    absolute_path=abs_path,
                    line_count=line_count,
                    agent_id=self.agent_id,
                    agent_name=self.agent_name
                )
                read_files_list.append(file_read)

            except Exception as e:
                # Log error but continue with other files
                print(f"Error processing read file {file_path}: {e}")
                continue

        return read_files_list if read_files_list else None

    def generate_metadata(self) -> AgentLogMetadata:
        """
        Generate complete metadata for this agent's file operations.

        Returns:
            AgentLogMetadata with all file changes and reads
        """
        file_changes = self.get_file_changes_metadata()
        read_files = self.get_read_files_metadata()

        return AgentLogMetadata(
            file_changes=file_changes,
            read_files=read_files,
            total_files_modified=len(self.modified_files) if self.modified_files else None,
            total_files_read=len(self.read_files) if self.read_files else None,
            generated_at=datetime.now().isoformat()
        )
