from typing import Dict, List, Any, Optional
from .base import GitHubClient


class ReposClient(GitHubClient):
    """GitHub Repositories API client."""
    
    def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information."""
        return self.get(f"/repos/{owner}/{repo}")
    
    def list_user_repos(self, username: str, type: str = "all", sort: str = "updated") -> List[Dict[str, Any]]:
        """List repositories for a user."""
        params = {"type": type, "sort": sort}
        return self.get_all_pages(f"/users/{username}/repos", params=params)
    
    def list_org_repos(self, org: str, type: str = "all", sort: str = "updated") -> List[Dict[str, Any]]:
        """List repositories for an organization."""
        params = {"type": type, "sort": sort}
        return self.get_all_pages(f"/orgs/{org}/repos", params=params)
    
    def create_repo(self, name: str, description: str = "", private: bool = False, **kwargs) -> Dict[str, Any]:
        """Create a new repository."""
        data = {
            "name": name,
            "description": description,
            "private": private,
            **kwargs
        }
        return self.post("/user/repos", json=data)
    
    def delete_repo(self, owner: str, repo: str) -> bool:
        """Delete a repository."""
        return self.delete(f"/repos/{owner}/{repo}")
    
    def get_contents(self, owner: str, repo: str, path: str = "", ref: str = None) -> Dict[str, Any]:
        """Get repository contents."""
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref else {}
        return self.get(endpoint, params=params)
    
    def create_file(self, owner: str, repo: str, path: str, message: str, content: str, branch: str = None) -> Dict[str, Any]:
        """Create a new file in repository."""
        import base64
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode()
        }
        if branch:
            data["branch"] = branch
        return self.post(f"/repos/{owner}/{repo}/contents/{path}", json=data)
    
    def update_file(self, owner: str, repo: str, path: str, message: str, content: str, sha: str, branch: str = None) -> Dict[str, Any]:
        """Update an existing file in repository."""
        import base64
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "sha": sha
        }
        if branch:
            data["branch"] = branch
        return self.patch(f"/repos/{owner}/{repo}/contents/{path}", json=data)
    
    def list_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository branches."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/branches")
    
    def get_branch(self, owner: str, repo: str, branch: str) -> Dict[str, Any]:
        """Get specific branch information."""
        return self.get(f"/repos/{owner}/{repo}/branches/{branch}")
    
    def list_tags(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository tags."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/tags")
    
    def list_releases(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository releases."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/releases")
    
    def get_release(self, owner: str, repo: str, release_id: int) -> Dict[str, Any]:
        """Get specific release."""
        return self.get(f"/repos/{owner}/{repo}/releases/{release_id}")
    
    def create_release(self, owner: str, repo: str, tag_name: str, name: str = None, body: str = "", draft: bool = False, prerelease: bool = False) -> Dict[str, Any]:
        """Create a new release."""
        data = {
            "tag_name": tag_name,
            "name": name or tag_name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease
        }
        return self.post(f"/repos/{owner}/{repo}/releases", json=data)
    
    def get_contributors(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Get repository contributors."""
        return self.get_all_pages(f"/repos/{owner}/{repo}/contributors")
    
    def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Get repository languages."""
        return self.get(f"/repos/{owner}/{repo}/languages")
    
    def get_readme(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository README."""
        return self.get(f"/repos/{owner}/{repo}/readme")