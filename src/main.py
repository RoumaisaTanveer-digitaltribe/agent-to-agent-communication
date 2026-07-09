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

MAX_REVISIONS = 2


@app.post("/run-task", response_model=TaskResponse)
def run_task(request: TaskRequest) -> TaskResponse:
    trace: list[AgentStep] = []

    # 1. Planner
    planner_input = {"task": request.task}
    planner_output = planner.run(planner_input)
    trace.append(
        AgentStep(
            agent_name="PlannerAgent",
            input=planner_input,
            output=planner_output,
        )
    )

    # 2. Researcher (first pass)
    researcher_output = researcher.run(planner_output)
    trace.append(
        AgentStep(
            agent_name="ResearcherAgent",
            input=planner_output,
            output=researcher_output,
        )
    )

    # 3. Critic (first pass)
    critic_output = critic.run(researcher_output)
    trace.append(
        AgentStep(
            agent_name="CriticAgent",
            input=researcher_output,
            output=critic_output,
        )
    )

    # 4. Revision loop — driven entirely by the Critic's own decision field,
    #    not by any hardcoded Python check. This is the real agent-to-agent
    #    decision point: the Critic's judgment controls whether the
    #    pipeline loops back or moves on to Writer.
    revisions = 0
    while critic_output["critic_decision"] == "revise" and revisions < MAX_REVISIONS:
        revision_input = {**critic_output, "critic_feedback": critic_output["critic_notes"]}

        researcher_output = researcher.run(revision_input)
        trace.append(
            AgentStep(
                agent_name="ResearcherAgent (revised)",
                input=revision_input,
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

        revisions += 1

    # 5. Writer — runs once, after the loop settles (approved, or hit max revisions)
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
        improvement_note=writer_output["improvement_note"],
        trace=trace,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}