"""Simple agent classes that pass structured dicts through a pipeline."""


class PlannerAgent:
    """Breaks a task into 2–3 actionable bullet steps."""

    def run(self, data: dict) -> dict:
        task = data["task"]
        words = task.split()
        if len(words) <= 4:
            steps = [
                f"Understand the request: {task}",
                f"Identify key deliverables for: {task}",
                f"Outline a concise response for: {task}",
            ]
        else:
            mid = len(words) // 2
            first_half = " ".join(words[:mid])
            second_half = " ".join(words[mid:])
            steps = [
                f"Analyze scope: {first_half}",
                f"Address remaining aspects: {second_half}",
                f"Synthesize findings into a final answer",
            ]
        return {"task": task, "steps": steps}


class ResearcherAgent:
    """Adds 1–2 simple details per step via string manipulation (no external APIs)."""

    def run(self, data: dict) -> dict:
        research: dict[str, list[str]] = {}
        for step in data["steps"]:
            topic = step.split(":")[-1].strip() if ":" in step else step
            details = [
                f"Context note: '{topic}' relates to common best practices.",
                f"Detail: consider constraints and audience when handling '{topic[:40]}'.",
            ]
            research[step] = details
        return {**data, "research": research}


class CriticAgent:
    """Checks for obvious gaps and adds short review notes."""

    def run(self, data: dict) -> dict:
        notes: list[str] = []
        if len(data["steps"]) < 2:
            notes.append("Warning: plan has fewer than 2 steps; coverage may be thin.")
        if len(data["task"]) < 10:
            notes.append("Note: task description is very short; assumptions were made.")
        uncovered = [s for s in data["steps"] if s not in data.get("research", {})]
        if uncovered:
            notes.append(f"Gap: {len(uncovered)} step(s) lack research details.")
        if not notes:
            notes.append("Review: plan and research look complete; proceed to writing.")
        return {**data, "critic_notes": notes}


class WriterAgent:
    """Produces the final combined response text."""

    def run(self, data: dict) -> dict:
        lines = [f"# Response to: {data['task']}", ""]
        lines.append("## Plan")
        for i, step in enumerate(data["steps"], start=1):
            lines.append(f"{i}. {step}")
        lines.append("")
        lines.append("## Research")
        for step, details in data.get("research", {}).items():
            lines.append(f"**{step}**")
            for detail in details:
                lines.append(f"  - {detail}")
        lines.append("")
        lines.append("## Review")
        for note in data.get("critic_notes", []):
            lines.append(f"- {note}")
        lines.append("")
        lines.append("## Summary")
        lines.append(
            f"Based on the plan, research, and review, here is the answer: "
            f"{data['task']} can be addressed by following the steps above "
            f"with attention to the noted constraints."
        )
        return {**data, "final_answer": "\n".join(lines)}
