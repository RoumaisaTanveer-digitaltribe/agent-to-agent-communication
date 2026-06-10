"""Agent classes powered by Mistral via OpenRouter."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL   = os.getenv("GPT_MODEL", "mistralai/mistral-small-3.2-24b-instruct:free")


def call_llm(system: str, user: str) -> str:
    """Single helper that all agents use to call Mistral."""
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "max_tokens": 500,
            "temperature": 0.3,
        },
        timeout=30,
    )
    if not response.ok:
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"].strip()


class PlannerAgent:
    """Breaks a task into 2-3 actionable steps using Mistral."""

    def run(self, data: dict) -> dict:
        task = data["task"]

        raw = call_llm(
            system="You are a planning assistant. Output only a numbered list of exactly 3 steps. No intro, no explanation.",
            user=f"Break this task into exactly 3 clear, actionable steps:\n\n{task}",
        )

        steps = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                step = line.lstrip("0123456789.-) ").strip()
                if step:
                    steps.append(step)

        if len(steps) < 2:
            steps = [line.strip() for line in raw.strip().splitlines() if line.strip()]

        return {"task": task, "steps": steps[:3]}


class ResearcherAgent:
    """Adds real research details per step using Mistral."""

    def run(self, data: dict) -> dict:
        research: dict[str, list[str]] = {}

        for step in data["steps"]:
            raw = call_llm(
                system="You are a research assistant. Output exactly 2 bullet points starting with -. Nothing else.",
                user=f"Give 2 short research notes (1 sentence each) for this step:\n\nStep: {step}\nTask: {data['task']}",
            )

            details = []
            for line in raw.strip().splitlines():
                line = line.strip().lstrip("-• ").strip()
                if line:
                    details.append(line)

            research[step] = details[:2] if details else [f"Research note for: {step}"]

        return {**data, "research": research}


class CriticAgent:
    """Reviews the plan and research using Mistral."""

    def run(self, data: dict) -> dict:
        steps_text = "\n".join(f"- {s}" for s in data["steps"])
        research_text = "\n".join(
            f"- {step}: {'; '.join(details)}"
            for step, details in data.get("research", {}).items()
        )

        raw = call_llm(
            system="You are a critical reviewer. Output only 1-2 short bullet points starting with -. No intro text.",
            user=f"Review this plan and research. Give 1-2 short review notes.\n\nTask: {data['task']}\nSteps:\n{steps_text}\nResearch:\n{research_text}",
        )

        notes = []
        for line in raw.strip().splitlines():
            line = line.strip().lstrip("-• ").strip()
            if line:
                notes.append(line)

        if not notes:
            notes = ["Plan and research look complete; proceed to writing."]

        return {**data, "critic_notes": notes[:3]}


class WriterAgent:
    """Writes the final response using Mistral."""

    def run(self, data: dict) -> dict:
        steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(data["steps"]))
        research_text = "\n".join(
            f"- {step}: {'; '.join(details)}"
            for step, details in data.get("research", {}).items()
        )
        critic_text = "\n".join(f"- {n}" for n in data.get("critic_notes", []))

        final_answer = call_llm(
            system="You are a professional writer. Write a clear, helpful response in plain markdown.",
            user=f"""Write a well-structured response to the task below using the plan, research, and review notes.

Task: {data['task']}

Plan:
{steps_text}

Research:
{research_text}

Review notes:
{critic_text}""",
        )

        return {**data, "final_answer": final_answer}