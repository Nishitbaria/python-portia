from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uvicorn


# Initialize FastAPI app
app = FastAPI(
    title="My FastAPI App",
    description="A simple FastAPI application with POST endpoint",
    version="1.0.0",
)


class UserPrompt(BaseModel):
    prompt: str


@app.post("/start-workflow")
def start_workflow(user_prompt: UserPrompt):
    """
    Start the workflow with the user's prompt
    """
    return {"message": "Workflow started successfully"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
