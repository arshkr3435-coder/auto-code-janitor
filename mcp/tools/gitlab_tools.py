import os
import base64
import httpx
from typing import Dict, Any, List

GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com/api/v4")
GITLAB_TOKEN = os.getenv("GITLAB_PERSONAL_ACCESS_TOKEN")

headers = {
    "Authorization": f"Bearer {GITLAB_TOKEN}",
    "Content-Type": "application/json"
}

async def get_repository_tree(project_id: str, branch: str = "main") -> Dict[str, Any]:
    """Retrieves the directory layout and configuration filenames from GitLab."""
    url = f"{GITLAB_URL}/projects/{project_id}/repository/tree"
    params = {"ref": branch, "recursive": True, "per_page": 100}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return {"error": f"Failed to fetch repo tree: {response.text}"}
        
        # Filter to return a clean list of file paths like our mock data
        files = [item["path"] for item in response.json() if item["type"] == "blob"]
        return {"files": files}

async def get_file_content(project_id: str, file_path: str, branch: str = "main") -> Dict[str, Any]:
    """Fetches and decodes raw text content of a specific file from GitLab."""
    # File path must be URL-encoded (e.g., models/transaction.py -> models%2Ftransaction.py)
    encoded_path = httpx.URL(file_path).path
    url = f"{GITLAB_URL}/projects/{project_id}/repository/files/{encoded_path}"
    params = {"ref": branch}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return {"error": f"Failed to fetch file content: {response.text}"}
        
        data = response.json()
        # GitLab returns file content as base64 encoded by default
        raw_content = base64.b64decode(data["content"]).decode("utf-8")
        return {"content": raw_content}

async def commit_code_changes(
    project_id: str, 
    branch: str, 
    commit_message: str, 
    actions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Applies multiple file actions (create, update, delete) in a single atomic GitLab commit."""
    url = f"{GITLAB_URL}/projects/{project_id}/repository/commits"
    
    # Map the agent's actions array directly to the GitLab Commits API payload format
    gitlab_actions = []
    for act in actions:
        gitlab_actions.append({
            "action": act["action"], # 'create', 'delete', or 'update'
            "file_path": act["file_path"],
            "content": act["content"]
        })
        
    payload = {
        "branch": branch,
        "commit_message": commit_message,
        "actions": gitlab_actions
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code not in [201, 200]:
            return {"error": f"Commit failed: {response.text}"}
        
        data = response.json()
        return {
            "status": "success",
            "commit_sha": data["id"],
            "branch": branch,
            "pipeline_id": data.get("last_pipeline", {}).get("id", "No active pipeline running")
        }