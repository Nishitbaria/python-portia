import json
import os
import datetime
from typing import Any, Dict
from portia import Plan, PlanRun, Step
from portia.execution_hooks import ExecutionHooks


class StreamingExecutionHooks:
    """Execution hooks that stream plan progress to a JSON file"""

    def __init__(self, stream_file_path: str = "plan_stream.json"):
        # Resolve to absolute path and ensure directory
        abs_path = os.path.abspath(stream_file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        self.stream_file_path = abs_path
        self.ensure_stream_file()

    def ensure_stream_file(self):
        """Ensure the stream file exists and is empty"""
        with open(self.stream_file_path, "w") as f:
            json.dump(
                {
                    "status": "waiting",
                    "plan_name": None,
                    "total_steps": 0,
                    "current_step": 0,
                    "current_step_name": None,
                    "current_step_tool": None,
                    "steps": [],
                    "started_at": None,
                    "last_updated": datetime.datetime.now().isoformat(),
                },
                f,
                indent=2,
            )
            try:
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                pass

    def write_stream_update(self, update_data: Dict[str, Any]):
        """Write an update to the stream file"""
        try:
            # Read current data
            with open(self.stream_file_path, "r") as f:
                current_data = json.load(f)

            # Update with new data
            current_data.update(update_data)
            current_data["last_updated"] = datetime.datetime.now().isoformat()

            # Write back to file
            with open(self.stream_file_path, "w") as f:
                json.dump(current_data, f, indent=2)
                try:
                    f.flush()
                    os.fsync(f.fileno())
                except Exception:
                    pass

        except Exception as e:
            print(f"Error writing stream update: {e}")

    def before_plan_run(self, plan: Plan, plan_run: PlanRun) -> None:
        """Called before the plan starts running"""
        # ReadOnlyPlan may not have a .name; derive a safe display name
        plan_name = (
            getattr(plan, "name", None)
            or getattr(plan, "title", None)
            or getattr(plan, "query", None)
            or f"Plan {getattr(plan, 'id', '')}"
        )
        try:
            print(f"🚀 Starting plan: {plan_name}")
        except Exception:
            print("🚀 Starting plan")

        # steps list may not be exposed on ReadOnlyPlan
        try:
            steps_list = list(getattr(plan, "steps", []) or [])
            total_steps = len(steps_list)
        except Exception:
            steps_list = []
            total_steps = 0

        # Pre-populate steps with pending status so viewer can render immediately
        steps_serialized = []
        for i, s in enumerate(steps_list):
            task = getattr(s, "task", f"Step {i+1}")
            tool_id = getattr(s, "tool_id", "unknown")
            steps_serialized.append(
                {
                    "step_number": i + 1,
                    "task": task,
                    "tool_id": tool_id,
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "output": None,
                    "error": None,
                }
            )

        # Print steps to console as requested
        if steps_serialized:
            print(f"📋 Total steps: {len(steps_serialized)}")
            for s in steps_serialized:
                print(
                    f"   • Step {s['step_number']}: {s['task']} (tool: {s['tool_id']})"
                )

        with open(self.stream_file_path, "w") as f:
            json.dump(
                {
                    "status": "running",
                    "plan_name": plan_name,
                    "plan_id": str(getattr(plan, "id", "")),
                    "plan_run_id": str(getattr(plan_run, "id", "")),
                    "total_steps": total_steps,
                    "current_step": 0,
                    "current_step_name": None,
                    "current_step_tool": None,
                    "started_at": datetime.datetime.now().isoformat(),
                    "steps": steps_serialized,
                    "last_updated": datetime.datetime.now().isoformat(),
                },
                f,
                indent=2,
            )
            try:
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                pass

    def before_step_execution(self, plan: Plan, plan_run: PlanRun, step: Step) -> None:
        """Called before each step starts"""
        step_index = getattr(plan_run, "current_step_index", 0)
        step_task = getattr(step, "task", "Unnamed step")
        step_tool = getattr(step, "tool_id", "unknown")
        print(f"📝 Starting step {step_index + 1}: {step_task}")

        # Read current data to preserve existing steps
        with open(self.stream_file_path, "r") as f:
            current_data = json.load(f)

        # Update current step info
        current_data.update(
            {
                "current_step": step_index + 1,
                "current_step_name": step_task,
                "current_step_tool": step_tool,
                "last_updated": datetime.datetime.now().isoformat(),
            }
        )

        # Ensure steps list covers this index
        while len(current_data["steps"]) <= step_index:
            current_data["steps"].append({})

        # Update step entry
        current_data["steps"][step_index].update(
            {
                "step_number": step_index + 1,
                "task": step_task,
                "tool_id": step_tool,
                "status": "running",
                "started_at": datetime.datetime.now().isoformat(),
                "completed_at": None,
            }
        )

        # Write update
        with open(self.stream_file_path, "w") as f:
            json.dump(current_data, f, indent=2)
            try:
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                pass

    def after_step_execution(
        self, plan: Plan, plan_run: PlanRun, step: Step, step_output: Any = None
    ) -> None:
        """Called after each step completes"""
        step_index = getattr(plan_run, "current_step_index", 0)
        step_task = getattr(step, "task", "Unnamed step")
        print(f"✅ Completed step {step_index + 1}: {step_task}")

        # Read current data
        with open(self.stream_file_path, "r") as f:
            current_data = json.load(f)

        # Get step output if available
        output_str = None
        try:
            if step_output is not None:
                output_str = str(step_output)
            elif hasattr(plan_run, "outputs") and hasattr(
                plan_run.outputs, "step_outputs"
            ):
                step_outputs = plan_run.outputs.step_outputs
                if getattr(step, "output", None) and step.output in step_outputs:
                    val = step_outputs[step.output].value
                    output_str = str(val)
            # Truncate if too long
            if output_str and len(output_str) > 200:
                output_str = output_str[:200] + "..."
        except Exception:
            output_str = "Output not available"

        # Update step completion info
        if step_index < len(current_data["steps"]):
            current_data["steps"][step_index].update(
                {
                    "status": "completed",
                    "completed_at": datetime.datetime.now().isoformat(),
                    "output": output_str,
                }
            )

        # Write update
        with open(self.stream_file_path, "w") as f:
            json.dump(current_data, f, indent=2)
            try:
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                pass

    def after_last_step(self, plan: Plan, plan_run: PlanRun) -> None:
        """Called after the plan completes"""
        plan_name = (
            getattr(plan, "name", None)
            or getattr(plan, "title", None)
            or getattr(plan, "query", None)
            or f"Plan {getattr(plan, 'id', '')}"
        )
        try:
            print(f"🎉 Plan completed: {plan_name}")
        except Exception:
            print("🎉 Plan completed")

        self.write_stream_update(
            {
                "status": "completed",
                "completed_at": datetime.datetime.now().isoformat(),
            }
        )


def create_streaming_hooks(
    stream_file_path: str = "plan_stream.json",
) -> ExecutionHooks:
    """Create execution hooks for streaming plan progress"""
    hooks = StreamingExecutionHooks(stream_file_path)

    return ExecutionHooks(
        before_plan_run=hooks.before_plan_run,
        before_step_execution=hooks.before_step_execution,
        after_step_execution=hooks.after_step_execution,
        after_last_step=hooks.after_last_step,
    )
