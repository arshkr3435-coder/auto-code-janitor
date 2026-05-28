import os
import pathlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
from src.mcp.client import handle_agent_tool_call
from pydantic import BaseModel
from typing import Optional


app = FastAPI(
    title="Auto-Code Janitor Agent API",
    description="Production-grade runtime gateway powered by Gemini 2.5."
)

# Initialize the official GenAI Client
ai_client = genai.Client()

class ChatRequest(BaseModel):
    prompt: str
    project_id: str
    
    # Dynamic Credentials passed by the user/frontend
    gitlab_token: Optional[str] = None
    gitlab_project_path: Optional[str] = None
    
    mongodb_uri: Optional[str] = None
    mongodb_database: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serves the dashboard directly using an absolute path resolution."""
    current_dir = pathlib.Path(__file__).parent
    template_path = current_dir / "templates" / "index.html"
    
    if not template_path.exists():
        return f"<h1>Template not found at: {template_path.absolute()}</h1>"
        
    return template_path.read_text(encoding="utf-8")

@app.post("/chat")
async def process_agent_turn(request: ChatRequest):
    try:
        # 1. Define the tools schema to hand over to Gemini's brain
        tools_config = [
            types.FunctionDeclaration(
                name="get_repository_tree",
                description="Retrieves the file layout structure of the target repository folder.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "project_id": {"type": "STRING"},
                        "branch": {"type": "STRING"}
                    },
                    "required": ["project_id"]
                }
            ),
            types.FunctionDeclaration(
                name="query_migration_knowledgebase",
                description="Queries MongoDB Atlas Vector Search for framework migration documentation rules.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "query_string": {"type": "STRING"},
                        "framework_context": {"type": "STRING"}
                    },
                    "required": ["query_string"]
                }
            )
        ]

        # 2. Package everything into a system instruction context
        system_instruction = (
            f"You are an expert software execution agent. Your job is to optimize codebases. "
            f"Always begin by exploring the directory tree layout using your tools. "
            f"Target project information: Project ID is {request.project_id} on branch {request.branch}."
        )

        # 3. Fire the initial execution request to Gemini
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=request.prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[types.Tool(function_declarations=tools_config)],
                temperature=0.2
            )
        )

        # 4. Parse if Gemini decided it needs to run a tool
        agent_thought = response.text if response.text else "Executing tool calls..."
        next_action = "reply_to_user"
        tool_response = None

        if response.function_calls:
            call = response.function_calls[0]
            next_action = call.name
            
            arguments = dict(call.args)
            if "project_id" not in arguments:
                arguments["project_id"] = request.project_id
            if "branch" not in arguments:
                arguments["branch"] = request.branch

            # Inject dynamic credential context properties into the arguments package
            arguments["gitlab_token"] = request.gitlab_token
            arguments["mongodb_uri"] = request.mongodb_uri
            arguments["mongodb_database"] = request.mongodb_database

            # Execute the real tool code passing along the dynamic credential map!
            tool_response = await handle_agent_tool_call(
                function_name=call.name,
                arguments=arguments
            )

        return {
            "user_prompt": request.prompt,
            "agent_thought": agent_thought,
            "next_action": next_action,
            "tool_response": tool_response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini core loop failure: {str(e)}")