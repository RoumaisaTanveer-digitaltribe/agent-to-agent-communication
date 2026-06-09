from fastapi import FastAPI

from src.agents import CriticAgent, PlannerAgent, ResearcherAgent, WriterAgent
from src.models import AgentStep, TaskRequest, TaskResponse

app = FastAPI(
    title="Multi-Agent Demo",
    description="A small pipeline of agents that process tasks step by step.",
    version="1.0.0",
)

planner = PlannerAgent()
researcher = ResearcherAgent()
critic = CriticAgent()
writer = WriterAgent()


@app.post("/run-task", response_model=TaskResponse)
def run_task(request: TaskRequest) -> TaskResponse:
    trace: list[AgentStep] = []

    planner_input = {"task": request.task}
    planner_output = planner.run(planner_input)
    trace.append(
        AgentStep(
            agent_name="PlannerAgent",
            input=planner_input,
            output=planner_output,
        )
    )

    researcher_output = researcher.run(planner_output)
    trace.append(
        AgentStep(
            agent_name="ResearcherAgent",
            input=planner_output,
            output=researcher_output,
        )
    )

    critic_output = critic.run(researcher_output)
    trace.append(
        AgentStep(
            agent_name="CriticAgent",
            input=researcher_output,
            output=critic_output,
        )
    )

    writer_output = writer.run(critic_output)
    trace.append(
        AgentStep(
            agent_name="WriterAgent",
            input=critic_output,
            output=writer_output,
        )
    )

    return TaskResponse(
        final_answer=writer_output["final_answer"],
        trace=trace,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
