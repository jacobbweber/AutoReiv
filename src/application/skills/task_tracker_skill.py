"""
Task Tracker Skill for General Assistant [REQ-AGENTS-002].
"""

from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class TaskTrackerSkill:
    """
    Skill providing task management capabilities backed by SQLite.
    """

    def __init__(self, store: SQLiteStateStore):
        self.store = store

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new user task."""
        return self.store.create_task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
        )

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List active or filtered user tasks."""
        return self.store.list_tasks(status=status, priority=priority)

    def update_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        """Update status of a task (e.g. pending, in_progress, completed, cancelled)."""
        res = self.store.update_task_status(task_id=task_id, status=status)
        if not res:
            return {"success": False, "error": f"Task '{task_id}' not found."}
        return {"success": True, "task": res, "status": status}

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task by ID."""
        deleted = self.store.delete_task(task_id=task_id)
        return {"success": deleted, "task_id": task_id}

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register task tracker tools with the scoped tool registry."""
        registry.register_tool(
            name="task_tracker_create",
            description="Create a new task in the user's task tracker.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the task"},
                    "description": {"type": "string", "description": "Optional details"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium",
                    },
                    "due_date": {"type": "string", "description": "Optional due date"},
                },
                "required": ["title"],
            },
            handler=self.create_task,
        )

        registry.register_tool(
            name="task_tracker_list",
            description="List tasks from the task tracker filtered by status or priority.",
            parameters={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "cancelled"],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                },
            },
            handler=self.list_tasks,
        )

        registry.register_tool(
            name="task_tracker_update",
            description="Update the status of an existing task.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "ID of task to update"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "cancelled"],
                    },
                },
                "required": ["task_id", "status"],
            },
            handler=self.update_task_status,
        )

        registry.register_tool(
            name="task_tracker_delete",
            description="Delete a task from the tracker.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "ID of task to delete"},
                },
                "required": ["task_id"],
            },
            handler=self.delete_task,
        )
