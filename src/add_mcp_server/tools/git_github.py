"""
Git + GitHub Tool - Complete local and remote operations
Uses GitHub API for all operations - NO CLI dependency required!
"""

import os
import base64
import requests
import subprocess
import shutil
from typing import Dict, Any, Union, List
from pathlib import Path


def github_api_request(method: str, endpoint: str, data=None) -> Dict[str, Any]:
    """Make GitHub API request."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        return {"error": "GITHUB_TOKEN environment variable required"}
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "MCP-Git-GitHub-Tool/2.0"
    }
    
    url = f"https://api.github.com{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        if response.status_code >= 400:
            return {"error": f"GitHub API error {response.status_code}: {response.text}"}
        
        return response.json() if response.content else {"success": True}
    except Exception as e:
        return {"error": str(e)}


def get_file_content(file_path: str) -> str:
    """Read file content and encode it."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def create_or_update_file(owner: str, repo: str, path: str, content: str, message: str, branch: str = "main") -> Dict[str, Any]:
    """Create or update a file via GitHub API."""
    
    # First, try to get the existing file to get its SHA
    get_response = github_api_request("GET", f"/repos/{owner}/{repo}/contents/{path}")
    
    data = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "branch": branch
    }
    
    # If file exists, we need the SHA for update
    if "sha" in get_response:
        data["sha"] = get_response["sha"]
    
    return github_api_request("PUT", f"/repos/{owner}/{repo}/contents/{path}", data)


def git_clone_to_clone_dir(repo_url: str, repo_name: str = None) -> Dict[str, Any]:
    """Clone a repository to the clone/ directory at project root."""
    try:
        # Déterminer la racine du projet (où se trouve src/)
        current_dir = Path.cwd()
        
        # Chercher le répertoire qui contient 'src'
        project_root = current_dir
        while project_root != project_root.parent:
            if (project_root / "src").exists():
                break
            project_root = project_root.parent
        else:
            # Si on ne trouve pas src/, utiliser le répertoire courant
            project_root = current_dir
        
        # Créer le répertoire clone à la racine
        clone_dir = project_root / "clone"
        clone_dir.mkdir(exist_ok=True)
        
        # Si aucun nom de repo spécifié, l'extraire de l'URL
        if not repo_name:
            if repo_url.endswith('.git'):
                repo_name = Path(repo_url).stem
            else:
                repo_name = repo_url.split('/')[-1]
        
        # Chemin de destination
        target_path = clone_dir / repo_name
        
        # Si le répertoire existe déjà, le supprimer
        if target_path.exists():
            shutil.rmtree(target_path)
        
        # Effectuer le clone
        result = subprocess.run([
            'git', 'clone', repo_url, str(target_path)
        ], capture_output=True, text=True, cwd=str(project_root))
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Repository cloned successfully to {str(target_path)}",
                "path": str(target_path),
                "project_root": str(project_root),
                "clone_dir": str(clone_dir)
            }
        else:
            return {
                "error": f"Git clone failed: {result.stderr}",
                "stdout": result.stdout
            }
            
    except FileNotFoundError:
        return {"error": "Git command not found. Please install Git."}
    except Exception as e:
        return {"error": f"Clone operation failed: {str(e)}"}


def run(operation: str, **params) -> Union[Dict[str, Any], str]:
    """Execute Git/GitHub operation using pure API calls."""
    
    # === GITHUB REPO OPERATIONS ===
    if operation == "create_repo":
        name = params.get('name')
        description = params.get('description', '')
        private = params.get('private', False)
        
        if not name:
            return {"error": "repository name required"}
        
        data = {
            "name": name,
            "description": description,
            "private": private
        }
        
        return github_api_request("POST", "/user/repos", data)
    
    elif operation == "get_user":
        username = params.get('username')
        if not username:
            return {"error": "username required"}
        
        return github_api_request("GET", f"/users/{username}")
    
    elif operation == "list_repos":
        username = params.get('username')
        if username:
            return github_api_request("GET", f"/users/{username}/repos")
        else:
            # List user's own repos
            return github_api_request("GET", "/user/repos")
    
    # === FILE OPERATIONS VIA API ===
    elif operation == "add_file":
        owner = params.get('owner')
        repo = params.get('repo')
        file_path = params.get('file_path')  # Local file path
        repo_path = params.get('repo_path')  # Path in repo
        message = params.get('message', f"Add {repo_path}")
        branch = params.get('branch', 'main')
        
        if not all([owner, repo, file_path, repo_path]):
            return {"error": "owner, repo, file_path, and repo_path required"}
        
        # Read local file content
        try:
            content = get_file_content(file_path)
            if content.startswith("Error reading file"):
                return {"error": content}
        except Exception as e:
            return {"error": f"Failed to read file {file_path}: {e}"}
        
        return create_or_update_file(owner, repo, repo_path, content, message, branch)
    
    elif operation == "add_multiple_files":
        owner = params.get('owner')
        repo = params.get('repo')
        files = params.get('files', [])  # List of {local_path, repo_path}
        message = params.get('message', "Add multiple files")
        branch = params.get('branch', 'main')
        
        if not all([owner, repo, files]):
            return {"error": "owner, repo, and files list required"}
        
        results = []
        for file_info in files:
            local_path = file_info.get('local_path')
            repo_path = file_info.get('repo_path')
            
            if not local_path or not repo_path:
                results.append({"error": f"Missing local_path or repo_path in {file_info}"})
                continue
            
            try:
                content = get_file_content(local_path)
                if content.startswith("Error reading file"):
                    results.append({"error": content, "file": local_path})
                    continue
                
                result = create_or_update_file(owner, repo, repo_path, content, f"{message} - {repo_path}", branch)
                results.append({"file": repo_path, "result": result})
                
            except Exception as e:
                results.append({"error": str(e), "file": local_path})
        
        return {"results": results, "total": len(files), "processed": len(results)}
    
    elif operation == "get_repo_contents":
        owner = params.get('owner')
        repo = params.get('repo')
        path = params.get('path', '')
        
        if not all([owner, repo]):
            return {"error": "owner and repo required"}
        
        endpoint = f"/repos/{owner}/{repo}/contents"
        if path:
            endpoint += f"/{path}"
            
        return github_api_request("GET", endpoint)
    
    elif operation == "create_branch":
        owner = params.get('owner')
        repo = params.get('repo')
        branch_name = params.get('branch_name')
        from_branch = params.get('from_branch', 'main')
        
        if not all([owner, repo, branch_name]):
            return {"error": "owner, repo, and branch_name required"}
        
        # Get the SHA of the source branch
        ref_response = github_api_request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{from_branch}")
        if "object" not in ref_response:
            return {"error": f"Could not get SHA for branch {from_branch}"}
        
        sha = ref_response["object"]["sha"]
        
        # Create new branch
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        
        return github_api_request("POST", f"/repos/{owner}/{repo}/git/refs", data)
    
    elif operation == "get_commits":
        owner = params.get('owner')
        repo = params.get('repo')
        branch = params.get('branch', 'main')
        count = params.get('count', 5)
        
        if not all([owner, repo]):
            return {"error": "owner and repo required"}
        
        endpoint = f"/repos/{owner}/{repo}/commits"
        params_dict = {"sha": branch, "per_page": count}
        
        response = requests.get(f"https://api.github.com{endpoint}", 
                              params=params_dict,
                              headers={
                                  "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
                                  "Accept": "application/vnd.github+json",
                                  "User-Agent": "MCP-Git-GitHub-Tool/2.0"
                              })
        
        if response.status_code >= 400:
            return {"error": f"GitHub API error {response.status_code}: {response.text}"}
        
        commits = response.json()
        return {
            "commits": [
                {
                    "sha": commit["sha"][:7],
                    "message": commit["commit"]["message"],
                    "author": commit["commit"]["author"]["name"],
                    "date": commit["commit"]["author"]["date"]
                }
                for commit in commits
            ]
        }
    
    # === GIT CLONE IMPLEMENTATION ===
    elif operation == "clone":
        repo_url = params.get('repo_url')
        repo_name = params.get('name')  # Nom optionnel du dossier
        
        if not repo_url:
            return {"error": "repo_url required for clone operation"}
        
        return git_clone_to_clone_dir(repo_url, repo_name)
    
    # === BACKWARD COMPATIBILITY (will use API) ===
    elif operation == "status":
        owner = params.get('owner')
        repo = params.get('repo')
        
        if not all([owner, repo]):
            return {"error": "owner and repo required for API status check"}
        
        # Get repo info to check status
        repo_info = github_api_request("GET", f"/repos/{owner}/{repo}")
        if "error" in repo_info:
            return repo_info
        
        return {
            "status": "API-managed",
            "last_push": repo_info.get("pushed_at"),
            "default_branch": repo_info.get("default_branch"),
            "size": repo_info.get("size")
        }
    
    elif operation == "add":
        return {"info": "Use 'add_file' or 'add_multiple_files' operations for API-based file management"}
    
    elif operation == "commit":
        return {"info": "Files are committed automatically when using 'add_file' operation"}
    
    elif operation == "push":
        return {"info": "Changes are pushed automatically when using API operations"}
    
    elif operation == "pull":
        return {"info": "Use 'get_repo_contents' to sync with remote repository"}
    
    elif operation == "branch":
        return {"info": "Use 'create_branch' operation for API-based branch management"}
    
    elif operation == "checkout":
        return {"info": "API operations work directly with branches. Specify branch in operations."}
    
    elif operation == "log":
        owner = params.get('owner')
        repo = params.get('repo')
        
        if not owner or not repo:
            return {"error": "owner and repo required. Use operation='get_commits' for full control."}
        
        return run("get_commits", **params)
    
    elif operation == "diff":
        owner = params.get('owner')
        repo = params.get('repo')
        base = params.get('base', 'main')
        head = params.get('head')
        
        if not all([owner, repo, head]):
            return {"error": "owner, repo, and head required for diff"}
        
        return github_api_request("GET", f"/repos/{owner}/{repo}/compare/{base}...{head}")
    
    else:
        return {"error": f"Unknown operation: {operation}"}


def spec() -> Dict[str, Any]:
    """Return the MCP function specification."""
    
    return {
        "type": "function",
        "function": {
            "name": "git_github",
            "description": "Complete Git + GitHub tool using pure API calls. No CLI dependency! Requires GITHUB_TOKEN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            # Repository management
                            "create_repo", "get_user", "list_repos",
                            # File operations (API-based)
                            "add_file", "add_multiple_files", "get_repo_contents",
                            # Branch management
                            "create_branch", "get_commits",
                            # Legacy operations (redirected to API)
                            "clone", "status", "add", "commit", "push", "pull", 
                            "branch", "checkout", "log", "diff"
                        ],
                        "description": "Git/GitHub operation. NEW API OPERATIONS: add_file, add_multiple_files, get_repo_contents, create_branch, get_commits. LEGACY: clone, status, add, commit, push, pull, branch, checkout, log, diff (now use API)"
                    },
                    # Repository identification
                    "owner": {
                        "type": "string",
                        "description": "Repository owner (username or org)"
                    },
                    "repo": {
                        "type": "string", 
                        "description": "Repository name"
                    },
                    # File operations
                    "file_path": {
                        "type": "string",
                        "description": "Local file path to upload"
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "Path in repository where to store the file"
                    },
                    "files": {
                        "type": "array",
                        "description": "Array of {local_path, repo_path} objects for multiple files"
                    },
                    # Branch operations
                    "branch": {
                        "type": "string",
                        "description": "Branch name (default: main)"
                    },
                    "branch_name": {
                        "type": "string",
                        "description": "New branch name to create"
                    },
                    "from_branch": {
                        "type": "string",
                        "description": "Source branch for new branch (default: main)"
                    },
                    # Commit operations
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "count": {
                        "type": "number",
                        "description": "Number of commits to retrieve (default: 5)"
                    },
                    # Clone operations
                    "repo_url": {
                        "type": "string",
                        "description": "Repository URL for cloning (e.g., https://github.com/user/repo.git)"
                    },
                    "remote": {
                        "type": "string",
                        "description": "[LEGACY] Git remote name - API operations don't need this"
                    },
                    # Repository creation
                    "name": {
                        "type": "string",
                        "description": "Repository name for creation OR custom directory name for clone"
                    },
                    "description": {
                        "type": "string",
                        "description": "Repository description"
                    },
                    "private": {
                        "type": "boolean",
                        "description": "Make repository private (default: false)"
                    },
                    "username": {
                        "type": "string",
                        "description": "GitHub username for user operations"
                    },
                    # Diff operations
                    "base": {
                        "type": "string",
                        "description": "Base branch for diff (default: main)"
                    },
                    "head": {
                        "type": "string",
                        "description": "Head branch for diff"
                    },
                    "path": {
                        "type": "string",
                        "description": "Path in repository for content operations"
                    }
                },
                "required": ["operation"],
                "additionalProperties": False
            }
        }
    }