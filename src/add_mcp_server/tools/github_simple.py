"""
Simple GitHub API Tool for MCP Server
Basic GitHub operations with clean interface.
"""

import os
from typing import Dict, Any, Union

# Try to import requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def run(operation: str, **params) -> Union[Dict[str, Any], str]:
    """Execute GitHub API operation."""
    
    if not REQUESTS_AVAILABLE:
        return {"error": "Missing dependency: pip install requests"}
    
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        return {"error": "GITHUB_TOKEN environment variable required"}
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "MCP-GitHub-Tool/1.0"
    }
    
    try:
        if operation == "get_user":
            username = params.get('username')
            if not username:
                return {"error": "username required"}
            response = requests.get(f"https://api.github.com/users/{username}", headers=headers)
            return response.json()
            
        elif operation == "get_repo":
            owner = params.get('owner')
            repo = params.get('repo')
            if not owner or not repo:
                return {"error": "owner and repo required"}
            response = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
            return response.json()
            
        elif operation == "list_repos":
            username = params.get('username')
            if not username:
                return {"error": "username required"}
            response = requests.get(f"https://api.github.com/users/{username}/repos", headers=headers)
            return response.json()
            
        elif operation == "list_user_repos":
            # List repos for the authenticated user
            response = requests.get("https://api.github.com/user/repos", headers=headers)
            return response.json()
            
        elif operation == "search_repos":
            query = params.get('query')
            if not query:
                return {"error": "query required"}
            response = requests.get(f"https://api.github.com/search/repositories?q={query}", headers=headers)
            return response.json()
            
        elif operation == "list_invitations":
            # List repository invitations for authenticated user
            response = requests.get("https://api.github.com/user/repository_invitations", headers=headers)
            return response.json()
            
        elif operation == "list_orgs":
            # List organizations for authenticated user
            response = requests.get("https://api.github.com/user/orgs", headers=headers)
            return response.json()
            
        else:
            return {"error": f"Unknown operation: {operation}"}
            
    except Exception as e:
        return {"error": str(e)}


def spec() -> Dict[str, Any]:
    """Return the MCP function specification."""
    
    status = "Ready" if REQUESTS_AVAILABLE else "Missing requests lib"
    
    return {
        "type": "function",
        "function": {
            "name": "github_simple",
            "description": f"GitHub API client ({status}) with authentication support",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string", 
                        "enum": ["get_user", "get_repo", "list_repos", "list_user_repos", "search_repos", "list_invitations", "list_orgs"],
                        "description": "GitHub operation to perform"
                    },
                    "username": {
                        "type": "string",
                        "description": "GitHub username"
                    },
                    "owner": {
                        "type": "string",
                        "description": "Repository owner"
                    },
                    "repo": {
                        "type": "string", 
                        "description": "Repository name"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["operation"],
                "additionalProperties": False
            }
        }
    }