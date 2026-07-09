from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    task: str = Field(..., min_length=1, description="The task for agents to process")


class AgentStep(BaseModel):
    agent_name: str
    input: dict
    output: dict


class TaskResponse(BaseModel):
    final_answer: str
    improvement_note: str
    trace: list[AgentStep]