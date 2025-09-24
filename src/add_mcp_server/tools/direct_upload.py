"""Direct GitHub Upload Tool - Upload content directly to GitHub via API."""

import os
import base64
import requests
from typing import Dict, Any


def run(owner: str, repo: str, repo_path: str, content: str, message: str = "Upload content") -> Dict[str, Any]:
    """Upload content directly to GitHub repository via API."""
    
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        return {"error": "GITHUB_TOKEN environment variable required"}
    
    # Prepare API request
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "MCP-Direct-Upload/1.0"
    }
    
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{repo_path}"
    
    # First, try to get the existing file to get its SHA (in case of update)
    try:
        get_response = requests.get(url, headers=headers)
        existing_file = get_response.json() if get_response.status_code == 200 else {}
    except:
        existing_file = {}
    
    # Prepare data for upload
    data = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }
    
    # If file exists, we need the SHA for update
    if "sha" in existing_file:
        data["sha"] = existing_file["sha"]
    
    # Upload content
    try:
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code >= 400:
            return {"error": f"GitHub API error {response.status_code}: {response.text}"}
        
        result = response.json()
        return {
            "success": True,
            "file": repo_path,
            "commit_sha": result.get("commit", {}).get("sha", "unknown")[:7],
            "html_url": result.get("content", {}).get("html_url", ""),
            "message": message,
            "size": len(content)
        }
        
    except Exception as e:
        return {"error": str(e)}


def spec() -> Dict[str, Any]:
    """Return the MCP function specification."""
    
    return {
        "type": "function",
        "function": {
            "name": "direct_upload",
            "description": "Upload content directly to GitHub repository via API. Requires GITHUB_TOKEN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "Repository owner (username or org)"
                    },
                    "repo": {
                        "type": "string", 
                        "description": "Repository name"
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "Path in repository where to store the content"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to upload"
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    }
                },
                "required": ["owner", "repo", "repo_path", "content"],
                "additionalProperties": False
            }
        }
    }