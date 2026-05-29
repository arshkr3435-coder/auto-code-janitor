import os
import base64
import httpx
from typing import Dict, Any, List

# Fallback defaults for the API base url endpoint
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com/api/v4")

async def get_repository_tree(project_id: str, branch: str = "main", **kwargs) -> Dict[str, Any]:
    """Retrieves the directory layout and configuration filenames from GitLab."""
    # Safe URL-encoding for namespaced project IDs (e.g., group/repo -> group%2Frepo)
    encoded_project_id = project_id.replace("/", "%2F")
    url = f"{GITLAB_URL}/projects/{encoded_project_id}/repository/tree"
    params = {"ref": branch, "recursive": True, "per_page": 100}
    
    # Dynamically extract the token passed by this specific user session
    token = kwargs.get("gitlab_token")
    if not token:
        return {"error": "Authentication Failed: Missing user 'gitlab_token' property in payload."}
        
    request_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=request_headers, params=params)
        if response.status_code != 200:
            return {"error": f"Failed to fetch repo tree: {response.text}"}
        
        # Filter to return a clean list of file paths like our mock data
        files = [item["path"] for item in response.json() if item["type"] == "blob"]
        return {"files": files}

async def get_file_content(project_id: str, file_path: str, branch: str = "main", **kwargs) -> Dict[str, Any]:
    """Fetches and decodes raw text content of a specific file from GitLab."""
    # Safe URL-encoding for namespaced project IDs and the inner target file path
    encoded_project_id = project_id.replace("/", "%2F")
    encoded_path = httpx.URL(file_path).path
    url = f"{GITLAB_URL}/projects/{encoded_project_id}/repository/files/{encoded_path}"
    params = {"ref": branch}
    
    # Dynamically extract the token passed by this specific user session
    token = kwargs.get("gitlab_token")
    if not token:
        return {"error": "Authentication Failed: Missing user 'gitlab_token' property in payload."}
        
    request_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=request_headers, params=params)
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
    actions: List[Dict[str, Any]],
    **kwargs
) -> Dict[str, Any]:
    """Applies multiple file actions (create, update, delete) in a single atomic GitLab commit."""
    # Safe URL-encoding for namespaced project IDs (e.g., group/repo -> group%2Frepo)
    encoded_project_id = project_id.replace("/", "%2F")
    url = f"{GITLAB_URL}/projects/{encoded_project_id}/repository/commits"
    
    # Dynamically extract the token passed by this specific user session
    token = kwargs.get("gitlab_token")
    if not token:
        return {"error": "Authentication Failed: Missing user 'gitlab_token' property in payload."}
        
    request_headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json"
    }
    
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
        response = await client.post(url, headers=request_headers, json=payload)
        if response.status_code not in [201, 200]:
            return {"error": f"Commit failed: {response.text}"}
        
        data = response.json()
        return {
            "status": "success",
            "commit_sha": data["id"],
            "branch": branch,
            "pipeline_id": data.get("last_pipeline", {}).get("id", "No active pipeline running")
        }