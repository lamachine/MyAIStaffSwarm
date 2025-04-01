from src.tools.base_tool import BaseTool

class ScheduleTaskTool(BaseTool):
    name = "schedule_task"
    description = "Schedules a task for a sub-agent."
    parameters = {
        "task_name": {"type": "string", "description": "The name of the task to schedule."},
        "due_time": {"type": "string", "description": "The due time for the task in ISO format."}
    }
    required = ["task_name", "due_time"]

    async def execute(self, deps: dict, *args, **kwargs) -> str:
        # Stub implementation: simply echo the task information.
        task_name = kwargs.get("task_name")
        due_time = kwargs.get("due_time")
        return f"Task '{task_name}' scheduled for {due_time}"

# Demo/test usage:
if __name__ == "__main__":
    import asyncio
    async def demo():
        tool = ScheduleTaskTool()
        result = await tool.execute({}, task_name="Daily Standup", due_time="2023-10-10T09:00:00Z")
        print(result)
    asyncio.run(demo()) 