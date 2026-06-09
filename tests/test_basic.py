from fastapi.testclient import TestClient
import pytest

from src.main import app
from src.agents import PlannerAgent, ResearcherAgent, CriticAgent, WriterAgent

EXPECTED_AGENTS = [
    "PlannerAgent",
    "ResearcherAgent",
    "CriticAgent",
    "WriterAgent",
]

client = TestClient(app)


# ──────────────────────────────────────────────
# /run-task endpoint tests
# ──────────────────────────────────────────────

def test_run_task_returns_final_answer_and_full_trace():
    response = client.post(
        "/run-task",
        json={"task": "Explain how to set up a simple FastAPI project"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["final_answer"]
    assert len(data["final_answer"]) > 0
    trace = data["trace"]
    assert len(trace) == len(EXPECTED_AGENTS)
    agent_names = [step["agent_name"] for step in trace]
    assert agent_names == EXPECTED_AGENTS
    for step in trace:
        assert isinstance(step["input"], dict)
        assert isinstance(step["output"], dict)


def test_run_task_rejects_empty_task():
    response = client.post("/run-task", json={"task": ""})
    assert response.status_code == 422


def test_run_task_rejects_missing_task_field():
    response = client.post("/run-task", json={})
    assert response.status_code == 422


def test_run_task_rejects_non_string_task():
    response = client.post("/run-task", json={"task": 12345})
    assert response.status_code == 422


def test_run_task_trace_has_correct_agent_order():
    response = client.post("/run-task", json={"task": "Write a short story about robots"})
    assert response.status_code == 200
    agent_names = [step["agent_name"] for step in response.json()["trace"]]
    assert agent_names == EXPECTED_AGENTS


def test_run_task_final_answer_contains_task():
    task = "Explain recursion in programming"
    response = client.post("/run-task", json={"task": task})
    assert response.status_code == 200
    assert task in response.json()["final_answer"]


def test_run_task_with_short_task():
    """Tasks with 4 words or fewer take the short-task branch in PlannerAgent."""
    response = client.post("/run-task", json={"task": "Fix the bug"})
    assert response.status_code == 200
    data = response.json()
    assert data["final_answer"]
    assert len(data["trace"]) == 4


def test_run_task_with_long_task():
    """Tasks with more than 4 words take the long-task branch in PlannerAgent."""
    response = client.post(
        "/run-task",
        json={"task": "Design a scalable microservices architecture for an e-commerce platform"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["final_answer"]
    steps = data["trace"][0]["output"]["steps"]
    assert len(steps) == 3


def test_run_task_final_answer_contains_plan_section():
    response = client.post("/run-task", json={"task": "How do I learn Python quickly"})
    assert response.status_code == 200
    assert "## Plan" in response.json()["final_answer"]


def test_run_task_final_answer_contains_research_section():
    response = client.post("/run-task", json={"task": "How do I learn Python quickly"})
    assert response.status_code == 200
    assert "## Research" in response.json()["final_answer"]


def test_run_task_final_answer_contains_review_section():
    response = client.post("/run-task", json={"task": "How do I learn Python quickly"})
    assert response.status_code == 200
    assert "## Review" in response.json()["final_answer"]


def test_run_task_final_answer_contains_summary_section():
    response = client.post("/run-task", json={"task": "How do I learn Python quickly"})
    assert response.status_code == 200
    assert "## Summary" in response.json()["final_answer"]


def test_run_task_planner_output_has_steps_key():
    response = client.post("/run-task", json={"task": "Build a REST API with authentication"})
    assert response.status_code == 200
    planner_output = response.json()["trace"][0]["output"]
    assert "steps" in planner_output
    assert isinstance(planner_output["steps"], list)


def test_run_task_researcher_output_has_research_key():
    response = client.post("/run-task", json={"task": "Build a REST API with authentication"})
    assert response.status_code == 200
    researcher_output = response.json()["trace"][1]["output"]
    assert "research" in researcher_output
    assert isinstance(researcher_output["research"], dict)


def test_run_task_critic_output_has_notes_key():
    response = client.post("/run-task", json={"task": "Build a REST API with authentication"})
    assert response.status_code == 200
    critic_output = response.json()["trace"][2]["output"]
    assert "critic_notes" in critic_output
    assert isinstance(critic_output["critic_notes"], list)


def test_run_task_writer_output_has_final_answer_key():
    response = client.post("/run-task", json={"task": "Build a REST API with authentication"})
    assert response.status_code == 200
    writer_output = response.json()["trace"][3]["output"]
    assert "final_answer" in writer_output


# ──────────────────────────────────────────────
# /health endpoint tests
# ──────────────────────────────────────────────

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_method_not_allowed():
    response = client.post("/health")
    assert response.status_code == 405


# ──────────────────────────────────────────────
# Unit tests — individual agents
# ──────────────────────────────────────────────

def test_planner_short_task_produces_three_steps():
    agent = PlannerAgent()
    result = agent.run({"task": "Fix bug"})
    assert len(result["steps"]) == 3


def test_planner_long_task_produces_three_steps():
    agent = PlannerAgent()
    result = agent.run({"task": "Explain how neural networks learn from data"})
    assert len(result["steps"]) == 3


def test_planner_output_contains_task_key():
    agent = PlannerAgent()
    result = agent.run({"task": "Write unit tests"})
    assert "task" in result
    assert result["task"] == "Write unit tests"


def test_researcher_adds_two_details_per_step():
    agent = ResearcherAgent()
    data = {
        "task": "some task",
        "steps": ["Step one: do this", "Step two: do that"],
    }
    result = agent.run(data)
    for step in data["steps"]:
        assert step in result["research"]
        assert len(result["research"][step]) == 2


def test_researcher_preserves_existing_keys():
    agent = ResearcherAgent()
    data = {"task": "Test task", "steps": ["Analyze: something"]}
    result = agent.run(data)
    assert result["task"] == "Test task"
    assert "steps" in result


def test_critic_adds_note_for_very_short_task():
    agent = CriticAgent()
    data = {
        "task": "Fix",
        "steps": ["step one", "step two"],
        "research": {"step one": [], "step two": []},
    }
    result = agent.run(data)
    notes_text = " ".join(result["critic_notes"])
    assert "short" in notes_text.lower() or "assumption" in notes_text.lower()


def test_critic_flags_missing_research_coverage():
    agent = CriticAgent()
    data = {
        "task": "Do something important",
        "steps": ["step one", "step two"],
        "research": {},  # no research for any step
    }
    result = agent.run(data)
    notes_text = " ".join(result["critic_notes"])
    assert "gap" in notes_text.lower()


def test_critic_clean_run_produces_proceed_note():
    agent = CriticAgent()
    steps = ["Step A: do this", "Step B: do that"]
    data = {
        "task": "A sufficiently long task description here",
        "steps": steps,
        "research": {s: ["detail"] for s in steps},
    }
    result = agent.run(data)
    notes_text = " ".join(result["critic_notes"]).lower()
    assert "proceed" in notes_text or "complete" in notes_text


def test_writer_final_answer_is_string():
    planner = PlannerAgent()
    researcher = ResearcherAgent()
    critic = CriticAgent()
    writer = WriterAgent()
    p = planner.run({"task": "Explain Docker containers"})
    r = researcher.run(p)
    c = critic.run(r)
    w = writer.run(c)
    assert isinstance(w["final_answer"], str)
    assert len(w["final_answer"]) > 0


def test_writer_final_answer_starts_with_response_header():
    planner = PlannerAgent()
    researcher = ResearcherAgent()
    critic = CriticAgent()
    writer = WriterAgent()
    task = "Explain Docker containers"
    p = planner.run({"task": task})
    r = researcher.run(p)
    c = critic.run(r)
    w = writer.run(c)
    assert w["final_answer"].startswith(f"# Response to: {task}")